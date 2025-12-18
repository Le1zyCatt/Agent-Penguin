# modules/msg/msg_handler.py
import os
import json
import time
import requests
from datetime import datetime
import config

from .doc_processor import extract_text_from_file
from modules.comic_translator.utils.paddle_ocr import image_to_base64

# 确保保存目录存在
os.makedirs(config.HISTORY_JSON_DIR, exist_ok=True)
MEDIA_LOG_DIR = os.path.join(config.DATA_DIR, "history_media")
os.makedirs(MEDIA_LOG_DIR, exist_ok=True)

# 在存储图片时调用ocr
def _perform_ocr(image_path):
    """
    调用本地 PaddleOCR 服务提取文字
    """
    if not os.path.exists(image_path):
        return ""
    
    try:
        # 1. 转 Base64
        b64 = image_to_base64(image_path)
        
        # 2. 请求 OCR API (使用 config 中的配置)
        payload = {"file": b64, "fileType": 1, "visualize": False}
        resp = requests.post(config.OCR_URL, json=payload, timeout=5)
        
        if resp.status_code == 200:
            res = resp.json()
            if res.get("errorCode", 1) == 0:
                # 3. 提取并拼接文字
                texts = []
                for page in res.get("result", {}).get("ocrResults", []):
                    for item in page.get("prunedResult", {}).get("res", []):
                        texts.append(item.get("text", ""))
                return " ".join(texts)
    except Exception as e:
        print(f"[MsgHandler] OCR 失败: {e}")
    
    return ""

def save_incoming_message(data: dict):
    """
    处理 NapCat 发来的消息，进行分类、过滤和保存
    """
    # 1. 确保发送的过来的json内容无误
    post_type = data.get("post_type")
    if post_type != "message":
        return {"status": "ignored", "reason": "not a message event"}

    raw_message = data.get("raw_message", "")

    # 2. 【过滤逻辑】不保存指令消息
    # 如果消息以 / 或 ! 开头，视为命令，不计入聊天历史
    if raw_message.strip().startswith(("/", "！", "!")):
        return {"status": "ignored", "reason": "command message"}

    # 3. 信息提取
    msg_type = data.get("message_type") # group / private
    
    if msg_type == "group":
        contact_id = str(data.get("group_id"))
        sender_name = data.get("sender", {}).get("nickname", "Unknown")
    else:
        contact_id = str(data.get("user_id"))
        sender_name = data.get("sender", {}).get("nickname", "Unknown")

    timestamp = data.get("time", int(time.time()))
    dt_object = datetime.fromtimestamp(timestamp)
    time_str = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    msg_id = str(data.get("message_id"))

    # 4. 【分类与清洗逻辑】
    content_type = "text"
    save_text = raw_message # 默认存原始内容
    local_path = ""
    extracted_content = ""
    
    # 图片处理
    if "image_path" in data:
        content_type = "image"
        local_path = data.get("image_path")
        save_text = "[图片]"
        
        # 立即执行 OCR
        print(f"[MsgHandler] 正在对图片进行 OCR: {local_path}...")
        ocr_text = _perform_ocr(local_path)
        if ocr_text:
            extracted_content = ocr_text
            print(f"[MsgHandler] OCR 成功，提取字符数: {len(ocr_text)}")
        else:
            extracted_content = "[OCR未识别到文字或服务不可用]"
    
    # 文件处理
    elif "file_path" in data:
        content_type = "file"
        local_path = data.get("file_path")
        file_name = os.path.basename(local_path)
        save_text = f"[文件: {file_name}]"
        # 立即读取文件
        print(f"[MsgHandler] 正在读取文件内容: {local_path}...")
        # 限制读取前 1000 字符，避免存太大的 JSON
        file_text = extract_text_from_file(local_path, max_chars=1000) 
        extracted_content = file_text
        print(f"[MsgHandler] 文件读取完成")

    # 5. 构造统一的记录结构
    new_record = {
        "id": msg_id,
        "name": sender_name,
        "time": time_str,
        "text": save_text,          # 简短文本，如 "[图片]"
        "content_type": content_type,
        "local_path": local_path,
        "extracted_content": extracted_content, # 【新字段】存 OCR 或文件内容
        "msgtype": msg_type
    }

    # 6. 【分流保存逻辑】
    # 策略：如果是纯文本，存入 history_json (用于 AI RAG/总结)
    # 如果是图片或文件，我们不仅存入 history_json (为了上下文完整)，但可以打个标记
    # 或者，如果你完全不想让图片文件干扰 AI 总结，可以在这里把图片/文件存到别的地方
    
    # 这里采用“全部存入但标记类型”的策略，并在 get_recent_messages 时过滤
    
    target_file = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    _append_to_json(target_file, new_record)

    return {"status": "saved", "type": content_type, "file": target_file}

def _append_to_json(file_path, record):
    """辅助函数：追加写入 JSON"""
    current_history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                current_history = json.load(f)
        except Exception:
            current_history = []
    
    current_history.append(record)
    
    # 保持最近 2000 条，防止文件过大
    if len(current_history) > 2000:
        current_history = current_history[-2000:]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(current_history, f, ensure_ascii=False, indent=2)

def get_recent_messages(contact_id: str, limit: int = 50, include_media: bool = True):
    """
    读取指定对象的最近 N 条消息
    新增参数 include_media: 是否包含图片/文件记录
    """
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    if not os.path.exists(file_path):
        # 尝试模糊匹配
        all_files = os.listdir(config.HISTORY_JSON_DIR)
        for f in all_files:
            if contact_id in f:
                file_path = os.path.join(config.HISTORY_JSON_DIR, f)
                break
        else:
             # 如果找不到文件，返回空字符串
            return ""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""

    collected_messages = []
    count = 0

    # 【核心逻辑修改】：倒序遍历 (从最新的消息开始往回找)
    # 这样可以确保我们找到 limit 条“符合条件”的消息，而不是先切片再过滤
    for item in reversed(data):
        if count >= limit:
            break
            
        c_type = item.get("content_type", "text")
        
        # 如果不包含媒体，且当前消息不是文本，则跳过
        if not include_media and c_type != "text":
            continue
        
        if c_type == "image" or c_type == "file":

            extra = item.get("extracted_content", "")
            invalid_keywords = ["[OCR未识别", "[读取文件出错", "[不支持", "[文件不存在"]
            if extra and not any(k in extra for k in invalid_keywords):
                display_text += f" (内容详情: {extra})"
            
        # 格式化消息行
        # 因为我们在 save 时已经清洗了 item['text']，这里直接用即可
        # 效果: "[12:00] User: [图片]" 或 "[12:01] User: 你好"
        line = f"[{item['time']}] {item['name']}: {item['text']}"
        collected_messages.append(line)
        count += 1

    # 因为是倒序找的，最后要反转回来，变成正常的时间顺序
    return "\n".join(reversed(collected_messages))