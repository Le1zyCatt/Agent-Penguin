# modules/msg/msg_handler.py
import os
import json
import time
from datetime import datetime
import config

# 确保保存目录存在
os.makedirs(config.HISTORY_JSON_DIR, exist_ok=True)

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
    # 如果消息以 / 开头，视为命令，不计入聊天历史
    if raw_message.strip().startswith("/"):
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

    # 4. 【分类逻辑】判断消息类型
    # 默认为文本
    content_type = "text"
    save_content = raw_message
    extra_info = {}

    # 检查是否为文件 (根据你提供的数据结构，文件包含 file_path)
    if "file_path" in data:
        content_type = "file"
        filename = raw_message.replace("[文件]", "")  # 移除前缀获取真实文件名
        save_content = f"[文件] {filename}"
        extra_info = {"local_path": data.get("file_path")}
    
    # 检查是否为图片 (根据你提供的数据结构，图片包含 image_path)
    elif "image_path" in data:
        content_type = "image"
        # 对于 RAG/总结，我们可能只需要知道这里发了张图，或者记录路径
        save_content = f"[图片]"
        extra_info = {"local_path": data.get("image_path")}

    # 5. 构造统一的记录结构
    new_record = {
        "id": msg_id,
        "name": sender_name,
        "time": time_str,
        "text": save_content,  # 用于显示/总结的内容
        "msgtype": msg_type,
        "content_type": content_type, # 新增字段：text/image/file
        **extra_info # 合并额外信息
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

def get_recent_messages(contact_id: str, limit: int = 50, include_media: bool = False):
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

    # 取最后 limit 条
    recent_data = data[-limit:] if len(data) > limit else data
    
    full_text_list = []
    for item in recent_data:
        # 【读取时的过滤】
        # 如果是 AI 总结 (include_media=False)，我们跳过图片和文件，只保留文本
        # 这里的逻辑可能需要修改：1. 最近50条消息要不要包括图片or文件（即找到50条全为文本的消息）
        # 默认是不包括图片or文字的
        c_type = item.get("content_type", "text")
        
        if not include_media and c_type != "text":
            continue 

        text_content = item['text']
        line = f"[{item['time']}] {item['name']}: {text_content}"
        full_text_list.append(line)
        
    return "\n".join(full_text_list)