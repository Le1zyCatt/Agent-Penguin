# server.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from contextlib import asynccontextmanager
import shutil
import os
import subprocess
import time
from typing import List

import config

from modules.msg.notifier import extract_important_messages
from scripts.vector_db_manager import VectorDBManager
from modules.msg.doc_processor import process_document_summary
from modules.msg.msg_handler import save_incoming_message, get_recent_messages, get_contact_list
from modules.msg.auto_reply import auto_reply  # 导入自动回复模块
#总结需要修改
from modules.msg.translator import BailianTranslator

# 全局状态
db_manager = None
ocr_process = None


# 初始化向量数据库和OCR服务
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager, ocr_process
    
    # 1. 启动OCR服务
    print("[System] 正在启动OCR服务...")
    try:
        # 使用conda环境执行命令
        cmd = [
            "conda", "run", "-n", "paddle-ocr",
            "paddlex", "--serve", "--pipeline", "./modules/comic_translator/OCR.yaml",
            "--host", "0.0.0.0",
            "--port", "8080"
        ]
        
        # 在后台启动OCR服务
        ocr_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # 增加等待时间，确保服务完全启动
        time.sleep(10)
        
        # 检查服务是否正常启动
        if ocr_process.poll() is None:
            print("[System] OCR服务启动成功")
        else:
            print("[System] ⚠️ OCR服务启动失败")
            # 打印启动失败的输出信息
            if ocr_process.stdout:
                stdout, _ = ocr_process.communicate()
                print(f"[OCR启动日志] {stdout}")
        
    except Exception as e:
        print(f"[System] ⚠️ OCR服务启动异常: {e}")
    
    # 2. 加载向量数据库
    print(f"[System] 正在加载向量数据库: {config.VECTOR_DB_PATH}")
    try:
        db_manager = VectorDBManager(db_path=config.VECTOR_DB_PATH) 
        print("[System] 向量数据库加载完毕")
    except Exception as e:
        print(f"[System] ⚠️ 数据库加载失败 (请检查路径): {e}")

    yield
    
    # 3. 关闭OCR服务
    if ocr_process and ocr_process.poll() is None:
        print("[System] 正在关闭OCR服务...")
        try:
            ocr_process.terminate()
            # 等待进程结束
            ocr_process.wait(timeout=5)
            print("[System] OCR服务已关闭")
        except subprocess.TimeoutExpired:
            print("[System] ⚠️ OCR服务关闭超时，强制终止")
            ocr_process.kill()
        except Exception as e:
            print(f"[System] ⚠️ 关闭OCR服务时发生异常: {e}")

app = FastAPI(lifespan=lifespan, title="MangaTranslator & ChatRAG API")
os.makedirs(config.TEMP_DIR, exist_ok=True)


# ===============================
# 功能：获取聊天对象列表
# ===============================
@app.get("/api/msg/list")
async def list_chats(type_filter: str = None):
    """
    获取聊天会话列表
    type_filter: 可选 "group" 或 "private"，不传则返回所有
    """
    try:
        all_contacts = get_contact_list()
        
        # 筛选逻辑
        if type_filter:
            filtered = [c for c in all_contacts if c["type"] == type_filter]
            return {"status": "success", "data": filtered}
            
        return {"status": "success", "data": all_contacts}
    except Exception as e:
        return {"status": "error", "msg": str(e)}



# ===============================
# 功能1：保存并自动回复
# ===============================
@app.post("/api/message/save")
async def save_msg(request: Request):
    """
    接收 NCatBot 发来的消息并保存
    """
    try:
        data = await request.json()
        # 调用 msg_handler 中的保存逻辑
        save_result = save_incoming_message(data)
        
        # 检查是否启用自动回复
        if config.AUTO_REPLY_ENABLED:
            print("[System] 自动回复已启用，正在生成回复...")
            
            # 提取自动回复所需的参数
            msg_type = data.get("message_type")  # group / private
            contact_id = str(data.get("group_id")) if msg_type == "group" else str(data.get("user_id"))
            current_message = data.get("raw_message", "")
            
            # 获取当前消息及其前50条消息
            recent_messages = get_recent_messages(contact_id, limit=50, include_media=True)
            
            # 调用自动回复模块，传入聊天历史
            reply_result = auto_reply(contact_id, current_message, msg_type, recent_messages)
            
            # 如果需要回复，则返回回复内容
            if reply_result.get("should_reply", False):
                reply_content = reply_result.get("reply_content", "")
                print(f"[AutoReply] 生成回复: {reply_content}")
                return {"status": "success", "detail": save_result, "reply": reply_content}
        
        # 默认不回复或自动回复未启用
        return {"status": "success", "detail": save_result, "reply": ""}
        
    except Exception as e:
        print(f"消息处理失败: {e}")
        return {"status": "error", "msg": str(e)}


# ===============================
# 功能2：查找聊天记录
# ===============================
@app.get("/api/chat/search")
async def search_chat(contact: str, query: str, k: int = 10):
    """
    在向量数据库中搜索聊天记录
    """
    if not db_manager:
        return {"results": [{"content": "错误：数据库未加载"}]}
    try:
        # 调用 vector_db_manager 的搜索
        # 注意：这里假设 db_manager.search_by_contact 返回的是 Document 对象列表
        results = db_manager.search_by_contact(contact, query, k)
        
        #使用百炼进行总结回答
        # if not results:
        #     return {
        #         "success": True, 
        #         "answer": "没有找到相关的聊天记录。", 
        #         "sources": []
        #     }

        # # 2. 拼接上下文供 AI 阅读
        # context_str = ""
        # sources = []
        # for r in results:
        #     meta = r.metadata
        #     # 拼接格式：[时间] 发送者: 内容
        #     snippet = f"[{meta.get('time', '未知时间')}] {meta.get('name', '未知')}: {r.page_content}"
        #     context_str += snippet + "\n"
        #     sources.append({"sender": meta.get('name'), "content": r.page_content})

        # # 3. 构建 Prompt
        # prompt = (
        #     f"你是一个聊天记录助手。请根据以下搜索到的聊天片段，回答用户的问题。\n"
        #     f"用户问题：{query}\n\n"
        #     f"聊天片段参考：\n{context_str}\n\n"
        #     f"请用自然流畅的语言回答，如果片段里没有答案，请直说。"
        # )

        # # 4. 调用 LLM (复用你的 translator)
        # translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        # # 这里复用 _call_api，mode 可以传 None 或自定义字符串让它透传 prompt
        # ai_answer = translator._call_api(prompt, mode="custom") 

        # return {
        #     "success": True,
        #     "answer": ai_answer,
        #     "sources": sources # 返回来源供前端参考
        # }

        # 最普通的返回
        data = [{"content": r.page_content, "metadata": r.metadata} for r in results]
        return {"results": data}
    except Exception as e:
        return {"results": [{"content": f"搜索出错: {str(e)}"}]}



# ===============================
# 功能3: 文档翻译与总结
# ===============================
@app.post("/api/doc/process")
async def process_doc(
    request: Request
):
    try:
        data = await request.json()
        file_path = data.get("file_path")
        # 核心点：这里接收 main.py 传过来的 task_type
        # 如果没传，默认就当作 summarize
        task_type = data.get("task_type", "summarize") 
        target_lang = data.get("target_lang", "Chinese")
        
        # 校验路径
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "error": f"文件路径不存在: {file_path}"}

        # 执行处理
        # process_document_summary 函数会根据 task_type 决定是总结还是翻译
        result_text = process_document_summary(file_path, task_type, target_lang)
        
        return {
            "success": True, 
            "task": task_type,
            "result": result_text
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

# ===============================
#  功能3: 消息总结   默认最近50条（或者根据时间范围限定，有待商榷）
# ===============================
# server.py

@app.post("/api/msg/summarize")
async def summarize_chat_history(
    contact_id: str = Form(...),      # 前端用户点击列表项后，传回这里的 ID (即群号)
    limit: int = Form(100),           # 总结条数，建议默认加大一点
    target_lang: str = Form("Chinese")
):
    """
    读取指定群/人的最近消息并调用 AI 总结
    """
    try:
        print(f"[Summarize] 收到总结请求 -> ID: {contact_id}, 条数: {limit}")
        
        # 1. 获取最近聊天文本
        # include_media=True 确保图片里的 OCR 文字也能被 AI 读到
        chat_text = get_recent_messages(contact_id, int(limit), include_media=True)
        
        if not chat_text:
            return {"success": False, "summary": f"未找到 ID 为 {contact_id} 的聊天记录，或记录为空。"}

        # 2. 构建 Prompt 或直接调用翻译器
        translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        
        summary = translator._call_api(chat_text, mode="summarize", target_lang=target_lang)
        
        return {"success": True, "summary": summary}

    except Exception as e:
        print(f"总结失败: {e}")
        return {"success": False, "summary": f"总结发生错误: {str(e)}"}



# ===============================
#  API 4: 重要消息提示
# ===============================
@app.post("/api/msg/notification")
async def msg_notification(
    contact_id: str = Form(...),  # 指定要检查的群号或QQ号
    limit: int = Form(100)        # 检查最近多少条
):
    """
    AI 智能提取指定会话中的重要消息（任务、DDL、文件等）
    """
    try:
        print(f"[Notification] 正在分析 {contact_id} 的重要消息...")
        result = extract_important_messages(contact_id, limit)
        return result
    except Exception as e:
        return {"success": False, "msg": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)