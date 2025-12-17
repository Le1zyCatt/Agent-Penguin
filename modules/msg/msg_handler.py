# modules/msg_handler.py
import os
import json
import time
from datetime import datetime
import config

# 确保保存目录存在
os.makedirs(config.HISTORY_JSON_DIR, exist_ok=True)

def save_incoming_message(data: dict):
    """
    处理 NapCat (OneBot v11) 发来的消息并保存到 JSON
    假设 data 是 OneBot v11 的 standard event 格式
    """
    # 1. 简单的过滤：只处理文本消息
    # NapCat 的消息格式通常包含 message_type, user_id, message 等
    post_type = data.get("post_type")
    if post_type != "message":
        return {"status": "ignored", "reason": "not a message event"}

    # 2. 提取关键信息
    # 如果是群聊，用 group_id 作为文件名；如果是私聊，用 user_id
    msg_type = data.get("message_type") # private / group
    
    if msg_type == "group":
        contact_id = str(data.get("group_id"))
        sender_name = data.get("sender", {}).get("nickname", "Unknown")
    else:
        contact_id = str(data.get("user_id"))
        sender_name = data.get("sender", {}).get("nickname", "Unknown")

    content = data.get("raw_message", "")
    timestamp = data.get("time", int(time.time()))
    
    # 格式化时间
    dt_object = datetime.fromtimestamp(timestamp)
    time_str = dt_object.strftime("%Y-%m-%d %H:%M:%S")

    # 3. 构造我们要保存的数据结构 (保持和你现有项目一致)
    # 参考 html_to_json.py 的结构: {"id":..., "name":..., "time":..., "text":...}
    new_record = {
        "id": str(data.get("message_id")),
        "name": sender_name,
        "time": time_str,
        "text": content,
        "msgtype": msg_type
    }

    # 4. 追加写入文件
    # 注意：为了性能，实际生产中通常用数据库，这里为了兼容现有逻辑继续用 JSON 文件
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    current_history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                current_history = json.load(f)
        except Exception:
            current_history = []
    
    current_history.append(new_record)
    
    # 简单的写回 (并发量大时会有风险，个人使用没问题)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(current_history, f, ensure_ascii=False, indent=2)

    return {"status": "saved", "file": file_path}

def get_recent_messages(contact_id: str, limit: int = 50):
    """
    读取指定对象的最近 N 条消息，并格式化为字符串
    """
    # 这里的 contact_id 可以是人名(如果文件名是人名) 或 QQ号(如果NapCat存的是QQ号)
    # 为了兼容，我们假设传入的就是文件名(不带.json)
    
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    if not os.path.exists(file_path):
        # 尝试看看有没有包含这个名字的文件 (模糊匹配)
        all_files = os.listdir(config.HISTORY_JSON_DIR)
        target_file = None
        for f in all_files:
            if contact_id in f:
                target_file = os.path.join(config.HISTORY_JSON_DIR, f)
                break
        
        if not target_file:
            raise FileNotFoundError(f"找不到关于 {contact_id} 的聊天记录")
        file_path = target_file

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 取最后 limit 条
    recent_data = data[-limit:] if len(data) > limit else data
    
    # 拼接文本
    full_text_list = []
    for item in recent_data:
        line = f"[{item['time']}] {item['name']}: {item['text']}"
        full_text_list.append(line)
        
    return "\n".join(full_text_list)