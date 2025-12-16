# server.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import shutil
import os
import threading
import subprocess
import time
from typing import List

# 1. 导入配置
import config

# 2. 导入旧项目 (scripts)
# 确保 scripts/__init__.py 存在
from scripts.vector_db_manager import VectorDBManager
# 这里的 api 逻辑可以重写在 server 里，也可以复用 topk_api_module
# 为了保持原汁原味，我们直接实例化 Manager，在接口里调用

# 3. 导入新模块 (modules)
from modules.comic_translator.core import process_comic_images
from modules.doc_processor import process_document_summary
from modules.msg_handler import save_incoming_message, get_recent_messages
# 复用 translator 来进行总结
from modules.comic_translator.translator import BailianTranslator

# 全局状态
paddlex_process = None
db_manager = None

# --- 生命周期：启动 OCR 和 加载数据库 ---
def start_ocr_service():
    global paddlex_process
    # 确保命令指向你的 conda 环境
    cmd = [
        "conda", "run", "-n", "paddle-ocr",
        "paddlex", "--serve", "--pipeline", "./modules/comic_translator/OCR.yaml",
        "--host", config.OCR_HOST, "--port", str(config.OCR_PORT)
    ]
    try:
        print("[System] 正在启动 PaddleX OCR...")
        paddlex_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(8) 
        if paddlex_process.poll() is None:
            print("[System] OCR 服务启动成功")
    except Exception as e:
        print(f"[System] OCR 启动失败: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动 OCR
    threading.Thread(target=start_ocr_service, daemon=True).start()
    
    # 2. 加载向量数据库 (Project B)
    global db_manager
    print(f"[System] 正在加载向量数据库: {config.VECTOR_DB_PATH}")
    try:
        # 显式传入 config 中的绝对路径
        db_manager = VectorDBManager(db_path=config.VECTOR_DB_PATH) 
        print("[System] 向量数据库加载完毕")
    except Exception as e:
        print(f"[System] ⚠️ 数据库加载失败 (请检查路径): {e}")

    yield
    
    # 清理
    if paddlex_process:
        paddlex_process.terminate()

app = FastAPI(lifespan=lifespan, title="MangaTranslator & ChatRAG API")
os.makedirs(config.TEMP_DIR, exist_ok=True)

# ===============================
#  API 1: 聊天记录 RAG (原 Project B)
# ===============================
@app.get("/api/chat/search")
async def search_chat(contact: str, query: str, k: int = 10):
    if not db_manager:
        return {"error": "数据库未加载"}
    try:
        # 直接调用 scripts.vector_db_manager 中的方法
        results = db_manager.search_by_contact(contact, query, k)
        # 序列化结果
        data = [{"content": r.page_content, "metadata": r.metadata} for r in results]
        return {"success": True, "results": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===============================
#  API 2: 消息总结 (新功能)
# ===============================
@app.post("/api/msg/summarize")
async def summarize_chat_history(
    contact_id: str = Form(..., description="聊天对象ID或文件名(不带.json)"),
    limit: int = Form(50, description="总结最近多少条消息"),
    target_lang: str = Form("Chinese", description="目标语言")
):
    """
    读取指定对象的最近聊天记录，发送给 AI 进行总结
    """
    try:
        # 1. 获取聊天文本
        chat_text = get_recent_messages(contact_id, limit)
        
        if not chat_text:
            return {"success": False, "error": "没有找到相关聊天记录"}

        # 2. 构建 Prompt (也可以直接用 mode='summarize')
        # 这里为了更精准的控制，我们稍微包装一下
        system_prompt = f"以下是与 {contact_id} 的聊天记录:\n\n{chat_text}\n\n"
        
        # 3. 调用 AI
        translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        # 复用 translator 的 _call_api，使用 summarize 模式
        summary = translator._call_api(system_prompt, mode="summarize", target_lang=target_lang)
        
        return {
            "success": True,
            "contact": contact_id,
            "processed_messages": limit,
            "summary": summary
        }

    except FileNotFoundError:
        return {"success": False, "error": f"找不到联系人 {contact_id} 的记录"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===============================
#  API 3: 通用文档翻译/总结 (新功能)
# ===============================
@app.post("/api/doc/process")
async def process_doc(
    file: UploadFile = File(...),
    task_type: str = Form("summarize"), # "summarize" 或 "translate"
    target_lang: str = Form("Chinese")
):
    temp_path = os.path.join(config.TEMP_DIR, file.filename)
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        # 调用文档处理器 (modules/doc_processor.py)
        result_text = process_document_summary(temp_path, task_type, target_lang)
        
        return {
            "success": True, 
            "filename": file.filename, 
            "task": task_type,
            "result": result_text
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)