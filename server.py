# server.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from contextlib import asynccontextmanager
import shutil
import os
from typing import List

import config

from scripts.vector_db_manager import VectorDBManager
from modules.msg.doc_processor import process_document_summary
from modules.msg.msg_handler import save_incoming_message, get_recent_messages
#总结需要修改
from modules.msg.translator import BailianTranslator

# 全局状态
db_manager = None


# 初始化向量数据库
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager
    print(f"[System] 正在加载向量数据库: {config.VECTOR_DB_PATH}")
    try:
        db_manager = VectorDBManager(db_path=config.VECTOR_DB_PATH) 
        print("[System] 向量数据库加载完毕")
    except Exception as e:
        print(f"[System] ⚠️ 数据库加载失败 (请检查路径): {e}")

    yield

app = FastAPI(lifespan=lifespan, title="MangaTranslator & ChatRAG API")
os.makedirs(config.TEMP_DIR, exist_ok=True)


# 接受并保存消息
@app.post("/api/message/save")
async def save_msg(request: Request):
    """
    接收 NCatBot 发来的消息并保存
    """
    try:
        data = await request.json()
        # 调用 msg_handler 中的保存逻辑
        save_result = save_incoming_message(data)
        return {"status": "success", "detail": save_result, "reply": ""} # 默认不回复
    except Exception as e:
        print(f"消息保存失败: {e}")
        return {"status": "error", "msg": str(e)}


# ===============================
# 功能1：查找聊天记录
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
# 功能2: 文档翻译与总结
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
@app.post("/api/msg/summarize")
async def summarize_chat_history(
    contact_id: str = Form(...),
    limit: int = Form(50),
    target_lang: str = Form("Chinese")
):
    """
    读取最近消息并调用 AI 总结
    """
    try:
        # 1. 获取最近聊天文本 (从 msg_handler)
        chat_text = get_recent_messages(contact_id, int(limit))
        
        if not chat_text:
            return {"summary": "未找到相关的聊天记录，无法总结。"}

        # 2. 调用 AI (复用 translator)
        translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        summary = translator._call_api(chat_text, mode="summarize", target_lang=target_lang)
        
        return {"summary": summary}

    except Exception as e:
        print(f"总结失败: {e}")
        return {"summary": f"总结发生错误: {str(e)}"}


# ===============================
#  API 3: 自动回复
# ===============================
@app.post("/api/msg/auto_response")
async def auto_response():
    return


# ===============================
#  API 4: 重要消息提示
# ===============================
@app.post("/api/msg/notification")
async def msg_notification():
    return



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)