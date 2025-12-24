# server.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import shutil
import os
import subprocess
import time
from typing import List
import shutil
import json

import config

from modules.msg.notifier import extract_important_messages
from scripts.vector_db_manager import MultiVectorDBManager
from modules.msg.doc_processor import extract_text_from_file, save_text_to_docx
from modules.msg.msg_handler import save_incoming_message, get_recent_messages, get_contact_list, get_recent_files, get_all_files, get_all_images
from modules.msg.auto_reply import auto_reply  # 导入自动回复模块
from modules.msg.translator import BailianTranslator as msg_trans
from modules.msg.reply_settings import get_reply_setting, set_reply_setting, get_all_reply_settings

from modules.comic_translator.utils.paddle_ocr import image_to_base64, ocr_image
from modules.comic_translator.utils.translator3 import BailianTranslator as img_trans
from modules.comic_translator.utils.cv_inpaint import process_image_with_ocr_data

# 全局状态
db_manager = None
multi_db_manager = None
ocr_process = None


# 初始化向量数据库和OCR服务
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager, multi_db_manager, ocr_process

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

    # 2. 加载多向量数据库管理器
    print(f"[System] 正在初始化多向量数据库管理器")
    try:
        multi_db_manager = MultiVectorDBManager(model_name="models/embedding/m3e-small")
        # 加载默认向量数据库
        success = multi_db_manager.switch_database(config.VECTOR_DB_PATH)
        if success:
            print("[System] 默认向量数据库加载完毕")
        else:
            print(f"[System] ⚠️ 默认数据库加载失败: {config.VECTOR_DB_PATH}")
    except Exception as e:
        print(f"[System] ⚠️ 多向量数据库管理器初始化失败: {e}")

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

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# 功能：获取特定聊天的所有文件
# ===============================
@app.get("/api/doc/list")
async def list_chat_files(contact_id: str):
    """
    获取指定会话中的所有文件列表
    前端调用此接口展示文件 -> 用户选择 -> 调用 /api/doc/translate
    """
    try:
        # 调用 handler 获取文件列表
        files = get_all_files(contact_id)
        
        return {
            "success": True, 
            "contact_id": contact_id,
            "count": len(files),
            "data": files
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===============================
# 功能：获取特定聊天的所有图片
# ===============================
@app.get("/api/image/list")
async def list_chat_images(contact_id: str):
    """
    获取指定会话中的所有图片列表
    前端调用此接口展示图片缩略图 -> 用户选择 -> 调用 /api/image/translate
    """
    try:
        images = get_all_images(contact_id)
        
        return {
            "success": True, 
            "contact_id": contact_id,
            "count": len(images),
            "data": images
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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

        # 提取自动回复所需的参数
        msg_type = data.get("message_type")  # group / private
        contact_id = str(data.get("group_id")) if msg_type == "group" else str(data.get("user_id"))

        # 检查是否启用自动回复（检查特定聊天的设置，如果没有则使用全局设置）
        if get_reply_setting(contact_id):
            print(f"[System] 聊天 {contact_id} 自动回复已启用，正在生成回复...")

            current_message = data.get("raw_message", "")

            # 检查是否被 @ 了，如果是则直接回复，跳过 whether_reply 判断
            is_at_me = data.get("is_at", False)

            # 如果 is_at 字段不存在或为 False，检查消息内容中是否包含机器人名称
            if not is_at_me:
                bot_name = getattr(config, 'BOT_NAME', '耄仙人')  # 获取配置中的机器人名称
                # 检查原始消息中是否包含机器人名称
                if bot_name in current_message:
                    is_at_me = True
                # 也检查是否是直接称呼机器人名字的消息
                elif current_message.strip().replace(" ", "").startswith(bot_name.replace(" ", "")):
                    is_at_me = True

            # 获取当前消息及其前50条消息
            recent_messages = get_recent_messages(contact_id, limit=50, include_media=True)

            # 如果是被 @ 的消息，则直接回复，跳过 whether_reply 判断
            if is_at_me:
                print("[System] 消息包含@，直接生成回复...")
                print(f"[Debug] 查询到的聊天数据: {recent_messages[:500]}...")  # 打印前500个字符用于调试
                # 调用自动回复模块，传入聊天历史，并设置 force_reply=True 跳过 whether_reply 判断
                reply_result = auto_reply(contact_id, current_message, msg_type, recent_messages, force_reply=True)

                # 如果有回复内容，则返回
                if reply_result.get("reply_content"):
                    reply_content = reply_result.get("reply_content", "")
                    print(f"[AutoReply] @触发回复: {reply_content}")
                    return {"status": "success", "detail": save_result, "reply": reply_content}
            else:
                # 没有被 @，按正常流程走 whether_reply 判断
                print(f"[Debug] 查询到的聊天数据: {recent_messages[:500]}...")  # 打印前500个字符用于调试
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
    if not multi_db_manager or not multi_db_manager.get_current_db():
        return {"results": [{"content": "错误：数据库未加载"}]}
    try:
        # 调用 multi vector_db_manager 的搜索
        results = multi_db_manager.search_by_contact(contact, query, k)

        # 最普通的返回
        data = [{"content": r.page_content, "metadata": r.metadata} for r in results]
        return {"results": data}
    except Exception as e:
        return {"results": [{"content": f"搜索出错: {str(e)}"}]}



# ===============================
# API 3.1: 多文档总结 (Summarize Recent Files)
# ===============================
@app.post("/api/doc/summarize")
async def summarize_docs(
    contact_id: str = Form(...), # 群号/用户ID
    limit: int = Form(5),        # 总结最近几个文件
    target_lang: str = Form("Chinese")
):
    try:
        # 1. 获取最近的文件列表
        files = get_recent_files(contact_id, limit)
        
        if not files:
            return {"success": False, "summary": "该对话最近没有发送过文件。"}

        # 2. 拼接所有文件的内容
        combined_text = ""
        file_names = []

        for f in files:
            file_names.append(f['name'])
            # 每次都重新读取文件，忽略历史记录中的 extracted_content
            print(f"[Doc] 正在实时读取文件: {f['path']}")
            content = extract_text_from_file(f['path'], max_chars=2000)

            combined_text += f"\n\n=== 文件名: {f['name']} (发送时间: {f['time']}) ===\n{content}"

        # 3. 构建 Prompt
        prompt = (
            f"以下是用户最近发送的 {len(files)} 个文件的内容片段。\n"
            f"请用{target_lang}对这些文件进行综合总结，指出它们之间的关联（如果有），"
            f"并提取每个文件的核心要点。\n\n"
            f"{combined_text}"
        )

        # 4. 调用 AI
        import time
        translator = msg_trans(config.DASHSCOPE_API_KEY)
        print(f"[Doc] 正在发送给AI的提示词:\n{prompt[:500]}...")  # 只示前500个字符
        start_time = time.time()
        summary = translator._call_api(prompt, mode="custom") # 使用 custom 模式透传 prompt
        end_time = time.time()
        print(f"[Doc] AI返回的摘要内容:\n{summary[:200]}...")  # 只示前200个字符
        print(f"[Doc] AI调用耗时: {end_time - start_time:.2f} 秒")

        return {
            "success": True,
            "summary": summary,
            "scanned_files": file_names
        }

    except Exception as e:
        print(f"文档总结出错: {e}")
        return {"success": False, "error": str(e)}


# ===============================
# API 3.2: 单文档翻译 (Translate & Download)
# ===============================
@app.post("/api/doc/translate")
async def translate_doc(
    file_path: str = Form(...),
    target_lang: str = Form("Chinese")
):
    try:
        print(f"[DocTranslate] 开始翻译文档，原始文件路径: {file_path}, 目标语言: {target_lang}")

        # 检查 file_path 是否为 None 或 undefined 或空字符串
        if not file_path or file_path == "undefined":
            print(f"[DocTranslate] 错误：文件路径为空或未定义")
            return {"success": False, "error": "文件路径不能为空"}

        # 规范化路径，解决可能的 ./ 问题
        normalized_path = os.path.normpath(file_path)
        print(f"[DocTranslate] 规范化后的文件路径: {normalized_path}")

        if not os.path.exists(normalized_path):
            print(f"[DocTranslate] 错误：文件不存在: {normalized_path}")
            return {"success": False, "error": "文件不存在"}

        print(f"[DocTranslate] 文件存在，开始读取内容...")
        # 1. 读取文件原文
        original_text = extract_text_from_file(file_path, max_chars=5000)
        print(f"[DocTranslate] 读取到的原文长度: {len(original_text) if original_text and not original_text.startswith('[') else 0}")

        if not original_text or original_text.startswith('['):
            print(f"[DocTranslate] 错误：无法读取文件内容或内容为空: {original_text}")
            return {"success": False, "error": "无法读取文件内容或内容为空"}

        # 2. 调用 AI 进行翻译
        print(f"[DocTranslate] 开始调用AI进行翻译...")
        translator = msg_trans(config.DASHSCOPE_API_KEY)
        translated_text = translator._call_api(original_text, mode="translate", target_lang=target_lang)
        print(f"[DocTranslate] AI翻译完成，翻译后文本长度: {len(translated_text) if translated_text else 0}")

        # 3. 生成翻译后的 Word 文档
        base_name = os.path.basename(file_path)
        name_no_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_no_ext}_translated.docx"

        # 确保输出目录存在
        output_dir = config.TRANS_DOC_PATH
        os.makedirs(output_dir, exist_ok=True)
        print(f"[DocTranslate] 输出目录: {output_dir}")

        output_path = os.path.join(output_dir, output_filename)
        print(f"[DocTranslate] 输出路径: {output_path}")

        save_text_to_docx(translated_text, output_path)
        print(f"[DocTranslate] Word文档已保存: {output_path}")

        # 4. 返回文件流供前端下载
        print(f"[DocTranslate] 准备返回文件: {output_path}")
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        print(f"[DocTranslate] 文档翻译出错: {e}")
        print(f"[DocTranslate] 错误类型: {type(e).__name__}")
        import traceback
        print(f"[DocTranslate] 错误堆栈: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}
    
# ===============================
# API 3.3: 单图片翻译 (Translate & Download)
# ===============================
@app.post("/api/image/translate")
async def translate_image(
    file_path: str = Form(...),      # 前端传来的原始图片绝对路径
    target_lang: str = Form("Chinese") # 目标语言
):
    """
    接收本地图片路径，执行 OCR -> 翻译 -> 回填，返回处理后的图片文件
    """
    # 1. 基础校验
    if not os.path.exists(file_path):
        return {"success": False, "error": f"图片文件不存在: {file_path}"}
        
    # 定义中间文件和最终输出文件的路径
    # 为了不污染原始保存目录，我们统一输出到 config.TEMP_DIR 或一个专门的 outputs 目录
    output_dir = config.TRANS_IMG_PATH
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    name_no_ext = os.path.splitext(filename)[0]
    
    # 中间 OCR JSON 结果文件
    ocr_json_path = os.path.join(output_dir, f"{name_no_ext}_ocr.json")
    # 翻译后的 JSON 结果文件
    translated_json_path = os.path.join(output_dir, f"{name_no_ext}_translated.json")
    # 最终生成的图片文件
    final_image_path = os.path.join(output_dir, f"{name_no_ext}_translated.jpg")

    try:
        print(f"[ImgTrans] 开始处理图片: {file_path}, 目标语言: {target_lang}")

        # 2. OCR 识别
        print("[ImgTrans] 正在进行 OCR...")
        base64_image = image_to_base64(file_path)
        # 调用你提供的 ocr_image 函数 (注意：确保 PaddleOCR 服务已启动)
        ocr_result = ocr_image(base64_image)
        
        # 保存 OCR 结果到临时 JSON (用于后续翻译和回填)
        with open(ocr_json_path, "w", encoding="utf-8") as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)

        # 3. 文本翻译
        print("[ImgTrans] 正在翻译文本...")
        # 初始化你提供的翻译器
        translator = img_trans(config.DASHSCOPE_API_KEY)
        # 调用翻译整个 JSON 文件的方法
        translated_data = translator.translate_json_file(ocr_json_path, target_lang=target_lang)
        
        # 保存翻译后的 JSON
        with open(translated_json_path, "w", encoding="utf-8") as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=2)

        # 4. 图片回填 (擦除原文本并写入新文本)
        print("[ImgTrans] 正在进行图片回填...")
        # 调用你提供的回填函数
        # 注意：需要提供一个支持中文的字体路径，在 config.py 中配置 FONT_PATH
        process_image_with_ocr_data(
            file_path,             # 原图路径
            translated_json_path,  # 翻译后的 JSON 路径
            final_image_path,      # 输出图片路径
            font_path=config.FONT_PATH # 字体路径
        )
        
        print(f"[ImgTrans] 处理完成，输出路径: {final_image_path}")

        # 5. 返回最终图片文件
        return FileResponse(
            path=final_image_path,
            filename=os.path.basename(final_image_path),
            media_type="image/jpeg"
        )

    except Exception as e:
        print(f"[ImgTrans] 图片翻译出错: {e}")
        # 出错时尝试清理临时文件
        for p in [ocr_json_path, translated_json_path]:
            if os.path.exists(p):
                os.remove(p)
        return {"success": False, "error": str(e)}
    finally:
        # 可选：清理中间 JSON 文件，保留最终图片
        if os.path.exists(ocr_json_path): os.remove(ocr_json_path)
        if os.path.exists(translated_json_path): os.remove(translated_json_path)


# ===============================
#  功能4: 消息总结   默认最近50条（或者根据时间范围限定，有待商榷）
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
        translator = msg_trans(config.DASHSCOPE_API_KEY)
        
        summary = translator._call_api(chat_text, mode="summarize", target_lang=target_lang)
        
        return {"success": True, "summary": summary}

    except Exception as e:
        print(f"总结失败: {e}")
        return {"success": False, "summary": f"总结发生错误: {str(e)}"}



# ===============================
#  API 5: 重要消息提示
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


# ===============================
#  API 6: 自动回复设置管理
# ===============================

@app.get("/api/reply/settings")
async def get_reply_settings(contact_id: str = None):
    """
    获取自动回复设置
    - 如果提供 contact_id，返回指定聊天的设置
    - 如果不提供 contact_id，返回所有聊天的设置
    """
    try:
        if contact_id:
            # 获取特定聊天的设置
            enabled = get_reply_setting(contact_id)
            return {
                "success": True,
                "contact_id": contact_id,
                "enabled": enabled
            }
        else:
            # 获取所有聊天的设置
            all_settings = get_all_reply_settings()
            return {
                "success": True,
                "settings": all_settings
            }
    except Exception as e:
        return {"success": False, "msg": str(e)}


@app.post("/api/reply/settings")
async def update_reply_settings(
    contact_id: str = Form(...),
    enabled: bool = Form(...)
):
    """
    更新指定聊天的自动回复设置
    """
    try:
        success = set_reply_setting(contact_id, enabled)
        if success:
            return {
                "success": True,
                "contact_id": contact_id,
                "enabled": enabled,
                "msg": f"已{'启用' if enabled else '禁用'} {contact_id} 的自动回复"
            }
        else:
            return {
                "success": False,
                "msg": "设置保存失败"
            }
    except Exception as e:
        return {"success": False, "msg": str(e)}


# ===============================
#  API 7: 向量数据库管理
# ===============================

@app.get("/api/vector-db/list")
async def list_vector_dbs():
    """
    获取所有可用的向量数据库列表
    """
    try:
        if not multi_db_manager:
            return {"success": False, "msg": "多向量数据库管理器未初始化"}

        available_dbs = multi_db_manager.get_available_databases(base_dir=config.DATA_DIR)
        current_db_path = multi_db_manager.get_current_db_path()

        return {
            "success": True,
            "databases": available_dbs,
            "current_db": current_db_path
        }
    except Exception as e:
        return {"success": False, "msg": str(e)}


@app.post("/api/vector-db/switch")
async def switch_vector_db(
    db_path: str = Form(...)
):
    """
    切换到指定的向量数据库
    """
    try:
        if not multi_db_manager:
            return {"success": False, "msg": "多向量数据库管理器未初始化"}

        success = multi_db_manager.switch_database(db_path)
        if success:
            return {
                "success": True,
                "current_db": multi_db_manager.get_current_db_path(),
                "msg": f"已成功切换到数据库: {db_path}"
            }
        else:
            return {
                "success": False,
                "msg": f"切换数据库失败: {db_path}"
            }
    except Exception as e:
        return {"success": False, "msg": str(e)}


@app.get("/api/vector-db/current")
async def get_current_vector_db():
    """
    获取当前使用的向量数据库信息
    """
    try:
        if not multi_db_manager:
            return {"success": False, "msg": "多向量数据库管理器未初始化"}

        current_db_path = multi_db_manager.get_current_db_path()
        if current_db_path:
            return {
                "success": True,
                "current_db": current_db_path
            }
        else:
            return {
                "success": False,
                "msg": "当前没有加载任何数据库"
            }
    except Exception as e:
        return {"success": False, "msg": str(e)}


# ===============================
# API 8: 文件服务 (Serve Local Files)
# ===============================
@app.get("/api/file")
async def serve_local_file(path: str = Query(...)):
    """
    提供本地文件访问服务
    注意：出于安全考虑，只允许访问特定目录下的文件
    """
    try:
        # 解码路径
        import urllib.parse
        decoded_path = urllib.parse.unquote(path)
        print(f"[FileService] Requested path: {decoded_path}")

        # 安全检查：确保路径在允许的目录范围内
        import os
        allowed_dirs = [
            config.DATA_DIR,  # data 目录
            os.path.join(config.BASE_DIR, "ncatbot", "data"),  # ncatbot data 目录
            os.path.join(config.BASE_DIR, "data", "received_images"),  # received_images 目录
            os.path.join(config.BASE_DIR, "data", "translated_images"),  # translated_images 目录
            os.path.join(config.BASE_DIR, "data", "server_history"),  # server_history 目录
            config.TEMP_DIR,  # received_images directory
            config.TRANS_IMG_PATH,  # translated_images directory
            config.HISTORY_JSON_DIR,  # server_history directory
            os.path.join(config.BASE_DIR, "data"),  # Main data directory
        ]

        # 规范化路径以防止路径遍历攻击
        normalized_path = os.path.normpath(decoded_path)
        print(f"[FileService] Normalized path: {normalized_path}")

        # 检查路径是否在允许的目录范围内 - also check subdirectories
        is_allowed = False
        print(f"[FileService] Checking if path is in allowed directories...")
        for allowed_dir in allowed_dirs:
            try:
                print(f"[FileService] Checking allowed dir: {allowed_dir}")
                if os.path.exists(allowed_dir):
                    # Use pathlib for more reliable path comparison
                    from pathlib import Path
                    allowed_path = Path(allowed_dir).resolve()
                    file_path = Path(normalized_path).resolve()

                    print(f"[FileService] Resolved allowed path: {allowed_path}, Resolved file path: {file_path}")

                    # Check if the file path is within the allowed directory
                    try:
                        # This will raise ValueError if file_path is not relative to allowed_path
                        file_path.relative_to(allowed_path)
                        is_allowed = True
                        print(f"[FileService] Path is allowed: {normalized_path} is within {allowed_dir}")
                        break
                    except ValueError:
                        # Path is not within the allowed directory
                        continue
            except Exception as dir_error:
                print(f"[FileService] Error checking directory {allowed_dir}: {dir_error}")
                continue

        # Additional check: if not in allowed directories, check other possible image locations
        if not is_allowed:
            # Check if the file exists in common image directories
            possible_dirs = [
                os.path.join(config.BASE_DIR, "ncatbot", "data"),  # ncatbot data directory
                config.DATA_DIR,  # main data directory
                config.TEMP_DIR,  # received images directory
                config.TRANS_IMG_PATH,  # translated images directory
            ]

            for possible_dir in possible_dirs:
                if os.path.exists(possible_dir):
                    # Check if normalized_path is relative and exists in this directory
                    if not os.path.isabs(normalized_path):
                        potential_path = os.path.join(possible_dir, normalized_path)
                        if os.path.exists(potential_path):
                            # Verify it's within the allowed directory
                            if os.path.commonpath([os.path.realpath(possible_dir), os.path.realpath(potential_path)]) == os.path.realpath(possible_dir):
                                normalized_path = potential_path
                                is_allowed = True
                                print(f"[FileService] Found image in {possible_dir}: {normalized_path}")
                                break
                    else:
                        # If it's an absolute path, check if it's under any of the allowed directories
                        if os.path.commonpath([os.path.realpath(possible_dir), os.path.realpath(normalized_path)]) == os.path.realpath(possible_dir):
                            is_allowed = True
                            print(f"[FileService] Absolute path is in allowed directory {possible_dir}: {normalized_path}")
                            break

        if not is_allowed:
            print(f"[FileService] Path not allowed: {normalized_path}")
            # Let's also print all allowed directories for debugging
            print(f"[FileService] Allowed directories: {allowed_dirs}")
            return {"success": False, "error": "访问被拒绝：不允许访问该路径"}

        if not os.path.exists(normalized_path):
            print(f"[FileService] File does not exist: {normalized_path}")
            print(f"[FileService] Available files in parent directory: {os.path.dirname(normalized_path)}")
            try:
                if os.path.exists(os.path.dirname(normalized_path)):
                    print(f"[FileService] Files in parent: {os.listdir(os.path.dirname(normalized_path))}")
            except Exception as e:
                print(f"[FileService] Error listing parent directory: {e}")
            return {"success": False, "error": "文件不存在"}

        # 根据文件扩展名确定 MIME 类型
        file_ext = os.path.splitext(normalized_path)[1].lower()
        print(f"[FileService] File extension: {file_ext}")
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }

        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        print(f"[FileService] Determined MIME type: {mime_type}")

        return FileResponse(
            path=normalized_path,
            media_type=mime_type,
            headers={"Cache-Control": "public, max-age=3600"}  # 缓存1小时
        )
    except Exception as e:
        print(f"[FileService] 文件服务出错: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ===============================
# API 9: 获取聊天历史 (用于前端本地搜索)
# ===============================
@app.get("/api/chat/history")
async def get_chat_history(contact_id: str):
    """
    获取指定联系人的完整聊天历史，用于前端本地搜索
    """
    try:
        import os
        import json

        # 构建文件路径
        file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")

        if not os.path.exists(file_path):
            return {"success": True, "history": []}

        # 读取聊天历史
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 返回完整的聊天历史，但只包含必要的字段用于搜索
        simplified_history = []
        for msg in data:
            simplified_msg = {
                "id": msg.get("id", ""),
                "name": msg.get("name", "Unknown"),
                "group_name": msg.get("group_name", ""),
                "time": msg.get("time", ""),
                "text": msg.get("text", ""),
                "content_type": msg.get("content_type", "text"),
                "extracted_content": msg.get("extracted_content", ""),
                "local_path": msg.get("local_path", ""),
                "msgtype": msg.get("msgtype", "")
            }
            simplified_history.append(simplified_msg)

        return {
            "success": True,
            "history": simplified_history,
            "count": len(simplified_history)
        }

    except Exception as e:
        print(f"[GetHistory] 获取聊天历史出错: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)