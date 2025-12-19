# modules/msg/notifier.py
import json
import logging
import config
from modules.msg.translator import BailianTranslator
from modules.msg.msg_handler import get_raw_recent_messages

def extract_important_messages(contact_id: str, limit: int = 100):
    """
    获取指定 ID 的最近消息，并使用 AI 筛选出重要消息。
    返回结构化的重要消息列表。
    """
    # 1. 获取原始数据
    raw_msgs = get_raw_recent_messages(contact_id, limit)
    if not raw_msgs:
        return {"success": False, "msg": "未找到聊天记录", "data": []}

    # 2. 数据预处理：精简发送给 AI 的数据量，节省 Token 并提高准确率
    # 我们只保留 AI 判断所需的字段
    messages_for_ai = []
    for msg in raw_msgs:
        base_text = msg.get("text", "") # 例如 "[图片]" 或 "[文件: xxx.docx]"
        extra_content = msg.get("extracted_content", "") # 这里已经是 OCR 或文件读取的结果了
        
        # 组装发给 AI 的内容
        # 如果有提取的内容（OCR文字/文件摘要），拼接到后面
        if extra_content and len(extra_content) > 1:
            # 限制长度，防止长篇小说把 Token 撑爆 (例如限制前 300 字符)
            final_content = f"{base_text} \n(内容详情: {extra_content[:300]}...)"
        else:
            final_content = base_text

        messages_for_ai.append({
            "id": msg.get("time"),   # 用时间字符串作为临时 ID
            "sender": msg.get("name", "Unknown"),
            "content": final_content
        })

    # 3. 如果没有消息，直接返回
    if not messages_for_ai:
        return {"success": True, "data": []}

    # 3. 构建 Prompt
    # 这里的关键是要求 AI 返回纯 JSON 格式
    prompt = (
        f"你是我的私人消息助理。请分析以下 {len(messages_for_ai)} 条聊天记录，"
        f"筛选出所有**重要消息**。\n"
        f"【判定标准】：\n"
        f"- 包含具体的任务分配、截止日期 (DDL)。\n"
        f"- 包含会议通知、地点变更。\n"
        f"- 包含重要的文件传输（如合同、作业、报告）。\n"
        f"- 包含紧急情况、报错信息或金钱交易。\n"
        f"- 忽略闲聊、表情包、打招呼。\n\n"
        f"【聊天记录】：\n{json.dumps(messages_for_ai, ensure_ascii=False)}\n\n"
        f"【输出要求】：\n"
        f"请只输出一个 JSON 列表，不要包含 Markdown 标记（如 ```json）。\n"
        f"列表中的每个对象包含以下字段：\n"
        f"- `time`: 原消息的时间\n"
        f"- `sender`: 发送者昵称\n"
        f"- `content`: 原消息内容\n"
        f"- `reason`: 为什么你认为这条重要（简短说明）\n\n"
        f"如果没有重要消息，返回空列表 []。"
    )

    # 4. 调用 AI
    try:
        translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        # 使用 mode="custom" 透传 prompt
        ai_response = translator._call_api(prompt, mode="custom")
        
        # 5. 清洗和解析 AI 返回的 JSON
        # 有时候 AI 会忍不住加 ```json ... ```，我们需要去掉
        clean_json = ai_response.replace("```json", "").replace("```", "").strip()
        
        important_list = json.loads(clean_json)
        
        return {
            "success": True, 
            "data": important_list, 
            "total_scanned": len(raw_msgs)
        }
        
    except json.JSONDecodeError:
        print(f"[Notifier] AI 返回的不是合法 JSON: {ai_response}")
        return {"success": False, "msg": "AI 解析失败", "data": []}
    except Exception as e:
        print(f"[Notifier] 执行出错: {e}")
        return {"success": False, "msg": str(e), "data": []}