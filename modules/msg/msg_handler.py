# modules/msg/msg_handler.py
import os
import json
import time
import requests
from datetime import datetime
import config

from .doc_processor import extract_text_from_file
from modules.comic_translator.utils.paddle_ocr import image_to_base64

os.makedirs(config.HISTORY_JSON_DIR, exist_ok=True)

def _perform_ocr(image_path):
    """
    调用本地 PaddleOCR 服务提取文字
    """
    if not os.path.exists(image_path):
        return ""
    
    try:
        # 1. 转 Base64
        b64 = image_to_base64(image_path)
        
        # 2. 请求 OCR API
        payload = {"file": b64, "fileType": 1, "visualize": False}
        resp = requests.post(config.OCR_URL, json=payload, timeout=5)
        
        if resp.status_code == 200:
            res = resp.json()
            if res.get("errorCode", 1) == 0:
                # 3. 修正：从正确的字段提取文字
                texts = []
                for page in res.get("result", {}).get("ocrResults", []):
                    pruned_result = page.get("prunedResult", {})
                    
                    # 方法1：从rec_texts字段提取
                    rec_texts = pruned_result.get("rec_texts", [])
                    if isinstance(rec_texts, list):
                        texts.extend([text for text in rec_texts if text])
                    elif isinstance(rec_texts, str) and rec_texts.strip():
                        # 如果rec_texts是字符串，尝试解析
                        try:
                            import ast
                            parsed_texts = ast.literal_eval(rec_texts)
                            if isinstance(parsed_texts, list):
                                texts.extend([text for text in parsed_texts if text])
                        except:
                            # 如果解析失败，直接使用
                            texts.append(rec_texts.strip())
                    
                    # 方法2：同时检查res字段（如果有的话）
                    for item in pruned_result.get("res", []):
                        text = item.get("text", "")
                        if text:
                            texts.append(text)
                
                result = " ".join(texts) if texts else ""
                print(f"[OCR] 提取到文字: {result}")
                return result
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
        # NapCat发送的群消息中没有sender字段，直接使用user_id作为发送者ID
        sender_id = str(data.get("user_id"))
        # 尝试从data中获取sender_name，如果没有则使用"Unknown"
        sender_name = data.get("sender_name", "Unknown")
    else:
        contact_id = str(data.get("user_id"))
        sender_id = contact_id
        # 尝试从data中获取sender_name，如果没有则使用"Unknown"
        sender_name = data.get("sender_name", "Unknown")

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
        "id": sender_id,  # 使用发送者的QQ号作为记录ID
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

# modules/msg/msg_handler.py

def get_recent_messages(contact_id: str, limit: int = 50, include_media: bool = True):
    """
    读取指定对象的最近 N 条消息
    contact_id: 对应文件名（通常是QQ号）
    include_media: 是否包含图片/文件记录（及其OCR内容）
    """
    # 1. 尝试直接拼接路径 (最快)
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    # 2. 如果文件不存在，尝试模糊匹配 (防止 contact_id 传进来不带后缀，或者文件名有差异)
    if not os.path.exists(file_path):
        found = False
        if os.path.exists(config.HISTORY_JSON_DIR):
            all_files = os.listdir(config.HISTORY_JSON_DIR)
            for f in all_files:
                # 假设 contact_id 是 "123456"，文件名是 "123456.json"
                if f == f"{contact_id}.json" or (contact_id in f and f.endswith(".json")):
                    file_path = os.path.join(config.HISTORY_JSON_DIR, f)
                    found = True
                    break
        
        if not found:
            print(f"[MsgHandler] 未找到联系人 {contact_id} 的聊天记录")
            return ""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[MsgHandler] 读取记录失败: {e}")
        return ""

    collected_messages = []
    count = 0

    # 倒序遍历：从最新消息开始往回找
    for item in reversed(data):
        if count >= limit:
            break
            
        c_type = item.get("content_type", "text")
        
        # 如果不包含媒体，且当前消息不是文本，则跳过
        if not include_media and c_type != "text":
            continue
        
        # 获取基础文本 (例如 "你好" 或 "[图片]" 或 "[文件: xxx.pdf]")
        msg_content = item.get("text", "")

        # 如果是媒体类型，且我们需要包含它，尝试追加 extracted_content
        if include_media and (c_type == "image" or c_type == "file"):
            extra = item.get("extracted_content", "")
            
            # 过滤无效的 OCR 结果，避免干扰 AI
            invalid_keywords = ["[OCR未识别", "[读取文件出错", "[不支持", "[文件不存在"]
            is_valid_extra = extra and not any(k in extra for k in invalid_keywords)
            
            if is_valid_extra:
                # 拼接格式： [图片] (内容详情: 图片里的文字...)
                msg_content += f" (内容详情: {extra})"
            
        # 格式化消息行
        # 结果示例: "[2023-10-27 10:00:00] 懒猫: [图片] (内容详情: 账单金额50元)"
        line = f"[{item['time']}] {item['name']}: {msg_content}"
        collected_messages.append(line)
        count += 1

    # 因为是倒序找的，最后要反转回来，变成正常的时间顺序 (旧 -> 新)
    return "\n".join(reversed(collected_messages))

def get_contact_list():
    """
    遍历 history 目录，返回所有聊天列表。
    文件名即为 contact_id (群号或好友QQ)。
    内容根据最后一条消息判断类型和时间。
    """
    if not os.path.exists(config.HISTORY_JSON_DIR):
        return []

    contacts = []
    files = os.listdir(config.HISTORY_JSON_DIR)
    
    for f in files:
        if not f.endswith(".json"):
            continue
            
        file_path = os.path.join(config.HISTORY_JSON_DIR, f)
        # 1. 获取 ID：文件名即 ID (如 "8937283.json" -> "8937283")
        contact_id = os.path.splitext(f)[0]
        
        try:
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                
            if not data:
                continue
            
            # 2. 获取元数据：基于最后一条消息
            last_msg = data[-1]
            msg_count = len(data)
            
            # 根据你提供的数据结构提取字段
            msg_type = last_msg.get("msgtype", "unknown")  # group / private
            last_time = last_msg.get("time", "")
            
            # 3. 构建返回对象
            contacts.append({
                "id": contact_id,       # 这是群号或好友QQ号 (用于传回给后端进行总结)
                "type": msg_type,       # "group" 或 "private" (前端可用来画图标)
                "count": msg_count,     # 消息条数
                "last_active": last_time, # 最后活跃时间
                "preview": last_msg.get("text", "")[:20] # 预览最后一条消息
            })
            
        except Exception as e:
            print(f"[MsgHandler] 读取列表文件 {f} 失败: {e}")
            continue

    # 4. 排序：按最后活跃时间倒序排列 (最新的在最前)
    # 注意：你的时间格式是 "2025-12-19 20:12:16"，可以直接字符串排序
    contacts.sort(key=lambda x: x["last_active"], reverse=True)

    return contacts

def get_raw_recent_messages(contact_id: str, limit: int = 100):
    """
    【新函数】获取原始的消息记录列表（字典格式），用于程序处理而非直接显示。
    """
    # 1. 尝试直接拼接路径
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    # 2. 只有当文件存在时才读取
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # 截取最近的 limit 条 (注意 data 是按时间正序存的，我们要最后 limit 条)
        recent_data = data[-limit:] if limit > 0 else data
        return recent_data
        
    except Exception as e:
        print(f"[MsgHandler] 读取原始记录失败: {e}")
        return []
    
def get_recent_files(contact_id: str, limit: int = 5):
    """
    【新函数】从聊天记录中查找最近发送的 n 个文件
    返回格式: [{"name": "test.docx", "path": "/abs/path/...", "time": "..."}]
    """
    # 复用之前的逻辑获取原始消息列表
    # 注意：这里我们取 limit*5 是为了防止最近几条全是文本，导致找不到文件，
    # 所以多取一点历史记录，然后再在内存里过滤
    raw_msgs = get_raw_recent_messages(contact_id, limit=limit * 10) 
    
    file_list = []
    # 倒序遍历（从最新到最旧）
    for msg in reversed(raw_msgs):
        if len(file_list) >= limit:
            break
            
        # 筛选 content_type 为 file 的消息
        if msg.get("content_type") == "file" and msg.get("local_path"):
            # 确保文件实际存在
            if os.path.exists(msg.get("local_path")):
                file_list.append({
                    "name": os.path.basename(msg.get("local_path")),
                    "path": msg.get("local_path"),
                    "time": msg.get("time"),
                    # 如果之前存过文件提取内容，也可以带上，省去重复读取
                    "extracted_content": msg.get("extracted_content", "") 
                })
    
    return file_list

def get_all_files(contact_id: str):
    """
    【新函数】获取指定联系人/群聊历史记录中的所有文件列表
    用于前端展示文件列表供用户选择翻译
    """
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    if not os.path.exists(file_path):
        return []

    file_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # 遍历所有记录 (倒序，让最新的文件排在前面)
        for msg in reversed(data):
            if msg.get("content_type") == "file":
                local_path = msg.get("local_path", "")
                
                # 仅返回依然存在于磁盘上的文件
                if local_path and os.path.exists(local_path):
                    file_list.append({
                        "file_name": os.path.basename(local_path),
                        "file_path": local_path,  # 这是传给翻译接口的关键参数
                        "sender": msg.get("name", "Unknown"),
                        "time": msg.get("time"),
                        "size": os.path.getsize(local_path) # 可选：返回文件大小
                    })
                    
    except Exception as e:
        print(f"[MsgHandler] 获取文件列表失败: {e}")
    
    return file_list


def get_all_images(contact_id: str):
    """
    【新函数】获取指定联系人/群聊历史记录中的所有图片列表
    用于前端展示图片列表供用户选择翻译
    """
    file_path = os.path.join(config.HISTORY_JSON_DIR, f"{contact_id}.json")
    
    if not os.path.exists(file_path):
        return []

    image_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # 倒序遍历，让最新的图片排在前面
        for msg in reversed(data):
            if msg.get("content_type") == "image":
                local_path = msg.get("local_path", "")
                
                # 仅返回依然存在于磁盘上的图片
                if local_path and os.path.exists(local_path):
                    image_list.append({
                        "file_name": os.path.basename(local_path),
                        "file_path": local_path,  # 这是传给翻译接口的关键参数
                        "sender": msg.get("name", "Unknown"),
                        "time": msg.get("time"),
                        # 可以选择性地返回已有的 OCR 内容作为预览
                        "ocr_preview": msg.get("extracted_content", "")[:50] 
                    })
                    
    except Exception as e:
        print(f"[MsgHandler] 获取图片列表失败: {e}")
    
    return image_list