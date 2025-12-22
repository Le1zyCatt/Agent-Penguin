# 自动回复模块

import requests
import json
import sys
import os

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))  # modules/msg/
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # Agent_Penguin/
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scripts import topk_api_module
from .whether_reply import whether_reply  # 导入 whether_reply 模块
import config  # 导入配置模块

# 百炼API配置
LLM_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
LLM_API_KEY = config.DASHSCOPE_API_KEY

# ===== 提示词 =====

PROMPT_TEMPLATE_PRIVATE = """
你是一个模仿别人说话的聊天专家，你擅长根据历史发言模仿一个人的语言和表达风格。
现在你看到了聊天对象给你发的消息：
{current_message}

根据这条消息，假如你要模仿的人以前和别人的聊天是这样的风格：
{conversation_history}

请生成给聊天对象的回复。请尽量根据给出的多条对话历史模仿语言和表达风格。
不要偏离对话历史的表达风格。
不要生成没有逻辑的回复。
不要有任何多余词句。
请只返回1条消息，不要换行，要有标点，不要太长。
"""

PROMPT_TEMPLATE_GROUP = """
你是一个模仿别人说话的聊天专家，你擅长根据历史发言模仿一个人的语言和表达风格。
现在你看到了聊天对象在群聊中发的消息：
{current_message}

根据这条消息，假如你要模仿的人以前和别人的聊天是这样的风格：
{conversation_history}

请生成给聊天对象的回复。请尽量根据给出的多条对话历史模仿语言和表达风格，但尽量不要用原话回复。
请只返回1条消息，不要换行，要有标点，不要太长。
"""

PROMPT_TEMPLATE_SHOULD_REPLY = """
你是一个智能助手，请判断是否需要回复以下消息。

聊天历史：
{conversation_history}

当前消息：
{current_message}

判断标准：
1. 是否直接向你提问或请求
2. 是否明确提及你
3. 是否需要你的回应才能继续对话

请只返回“需要回复”或“不需要回复”，不要添加任何其他内容。
"""

# ===== 主函数（接口不变） =====

def auto_reply(contact_name: str, current_message: str, msgtype: str, chat_history: str = "", force_reply: bool = False) -> dict:
    """
    自动回复主函数
    :param contact_name: 联系人名称
    :param current_message: 当前消息
    :param msgtype: 消息类型 (private/group)
    :param chat_history: 聊天历史
    :param force_reply: 强制回复标志，如果为 True 则跳过 whether_reply 判断
    """
    print(f"[AutoReply Debug] 开始处理自动回复")
    print(f"[AutoReply Debug] 联系人: {contact_name}")
    print(f"[AutoReply Debug] 当前消息: {current_message}")
    print(f"[AutoReply Debug] 消息类型: {msgtype}")
    print(f"[AutoReply Debug] 强制回复模式: {force_reply}")
    print(f"[AutoReply Debug] 聊天历史预览: {chat_history[:300]}...")  # 打印前300个字符用于调试

    if msgtype == "private":
        PROMPT_TEMPLATE = PROMPT_TEMPLATE_PRIVATE
    elif msgtype == "group":
        PROMPT_TEMPLATE = PROMPT_TEMPLATE_GROUP
    else:
        PROMPT_TEMPLATE = PROMPT_TEMPLATE_PRIVATE

    # =====================================================
    # Step 1：判断是否需要回复（除非强制回复）
    # =====================================================
    if not force_reply:
        # 使用 whether_reply 模块判断是否需要回复
        # 将 chat_history 转换为 whether_reply 需要的格式
        history_list = parse_chat_history(chat_history)
        print(f"[AutoReply Debug] 解析后的聊天历史: {history_list[:3]}...")  # 打印前3条用于调试

        should_reply_result = whether_reply(contact_name, current_message, history_list)
        print(f"[AutoReply Debug] whether_reply 结果: {should_reply_result}")

        if not should_reply_result.get("should_reply", False):
            return {
                "should_reply": False,
                "reply_content": "",
                "reason": should_reply_result.get("reason", "模型判断不需要回复")
            }
    else:
        # 如果是强制回复模式（例如被@时），跳过 whether_reply 判断
        print("[AutoReply] 强制回复模式，跳过 whether_reply 判断")

    # =====================================================
    # Step 2：确认需要回复 → 从向量库提取历史风格回复
    # =====================================================
    conversation_history = []

    try:
        search_results = topk_api_module.search_messages_api(
            #contact_name,
            "OmoT",
            current_message,
            k=config.TOP_K,
            n=config.NEXT_N,
        )
        print(f"[AutoReply Debug] 向量库搜索结果: {search_results.get('success', False)}")

        if search_results.get("success", False):
            for result in search_results.get("results", [])[:100]:
                replies = result.get("next_messages", [])
                if replies:
                    reply_content = replies[0].get("content", "").replace("[表情]", "")
                    if reply_content:
                        conversation_history.append(reply_content)

    except Exception as e:
        print(f"获取历史聊天风格失败: {e}")

    print(f"[AutoReply Debug] 从向量库获取的历史回复数量: {len(conversation_history)}")
    if conversation_history:
        print(f"[AutoReply Debug] 历史回复预览: {conversation_history[:3]}")  # 打印前3条用于调试

    if not conversation_history:
        return {
            "should_reply": False,
            "reply_content": "",
            "reason": "未找到可用的历史风格回复"
        }

    # =====================================================
    # Step 3：生成最终回复
    # =====================================================
    prompt = PROMPT_TEMPLATE.format(
        conversation_history="\n".join(conversation_history),
        current_message=current_message
    )
    print(f"[AutoReply Debug] 生成回复的提示词预览: {prompt[:500]}...")  # 打印前500个字符用于调试

    llm_response = call_llm_api(prompt)

    if not llm_response.get("success", False):
        return {
            "should_reply": False,
            "reply_content": "",
            "reason": f"生成回复失败: {llm_response.get('error', '未知错误')}"
        }

    reply_content = llm_response.get("content", "").strip()
    print(f"[AutoReply Debug] 生成的回复内容: {reply_content}")

    if not reply_content:
        return {
            "should_reply": False,
            "reply_content": "",
            "reason": "生成的回复内容为空"
        }

    return {
        "should_reply": True,
        "reply_content": reply_content,
        "reason": "成功生成回复"
    }


def parse_chat_history(chat_history: str) -> list:
    """
    将聊天历史字符串解析为 whether_reply 模块需要的格式
    :param chat_history: 格式为 "[时间] 发送者: 内容" 的字符串
    :return: [{"sender": "name", "content": "message", "time": "timestamp"}] 格式的列表
    """
    if not chat_history:
        return []

    lines = chat_history.strip().split('\n')
    history_list = []

    for line in lines:
        if not line.strip():
            continue

        # 解析格式: [2023-10-27 10:00:00] 懒猫: [图片] (内容详情: 图片里的文字...)
        if '] ' in line and ':' in line.split('] ')[1] if len(line.split('] ')) > 1 else False:
            try:
                time_and_sender, content = line.split('] ', 1)
                time_part = time_and_sender[1:]  # 去掉开头的 [
                sender, content = content.split(': ', 1)

                history_list.append({
                    "sender": sender.strip(),
                    "content": content.strip(),
                    "time": time_part
                })
            except:
                # 如果解析失败，跳过这一行
                continue

    return history_list

# ===== LLM API =====

def call_llm_api(prompt: str) -> dict:
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}"
        }

        payload = {
            "model": "qwen-plus",
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "max_tokens": 2000,
                "temperature": 0.3
            }
        }

        response = requests.post(
            LLM_API_URL,
            headers=headers,
            json=payload,
            timeout=300
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API请求失败: {response.status_code}, {response.text}"
            }

        result = response.json()

        if "output" in result and "text" in result["output"]:
            return {
                "success": True,
                "content": result["output"]["text"].strip()
            }

        if "output" in result and "choices" in result["output"]:
            return {
                "success": True,
                "content": result["output"]["choices"][0]["message"]["content"].strip()
            }

        return {
            "success": False,
            "error": f"API返回格式异常: {result}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"API调用异常: {str(e)}"
        }

# ===== 本地测试 =====

if __name__ == "__main__":
    result = auto_reply(
        contact_name="OmoT",
        current_message="我是你爸",
        msgtype="group",
        chat_history="A：你在吗\nB：怎么了"
    )

    print(result)
