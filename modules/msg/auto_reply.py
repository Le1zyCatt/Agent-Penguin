# auto_reply.py
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
import config  # 导入配置模块

# 百炼API配置
LLM_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  # 百炼API地址
LLM_API_KEY = config.DASHSCOPE_API_KEY  # 使用配置文件中的API密钥

# 提示词模板
PROMPT_TEMPLATE_PRIVATE = """
你是一个模仿别人说话的聊天专家，你擅长根据历史发言模仿一个人的的语言和表达风格。
现在你看到了聊天对象给你发的消息：
{current_message}

根据这条消息，假如你要模仿的人以前是这么回复的：
{conversation_history}

请生成给聊天对象的回复。请尽量根据给出的多条对话历史模仿语言和表达风格。不要偏离对话历史的表达风格。请生成不要生成没有逻辑的回复。
不要把没有关联的事情拼接在一起，不要有任何其他的多余词句。
请只返回1条消息，不要换行。

"""

PROMPT_TEMPLATE_GROUP = """
你是一个模仿别人说话的聊天专家，你擅长根据历史发言模仿一个人的的语言和表达风格。
现在你看到了聊天对象在群聊中发的消息：
{current_message}

根据这条消息，假如你要模仿的人以前是这么回复的：
{conversation_history}

请生成给聊天对象的回复。请尽量根据给出的多条对话历史模仿语言和表达风格。不要偏离对话历史的表达风格。请生成不要生成没有逻辑的回复。
不要把没有关联的事情拼接在一起，不要有任何其他的多余词句。
请只返回1条消息，不要换行。
在生成回复之前，有必要决定是否应该回复。如果该条消息没有强烈提及你，或者没有与你相关的意思，那么就返回空字符串。
"""

def auto_reply(contact_name: str, current_message: str, msgtype: str) -> dict:
    if msgtype == "private":
        PROMPT_TEMPLATE = PROMPT_TEMPLATE_PRIVATE
    elif msgtype == "group":
        PROMPT_TEMPLATE = PROMPT_TEMPLATE_GROUP
    """
    自动回复功能主函数
    
    Args:
        contact_name (str): 聊天对象姓名
        current_message (str): 当前用户输入的消息
        auto_reply_enabled (bool): 是否启用自动回复
        
    Returns:
        dict: 包含是否需要回复和回复内容的字典
    """
    # if not auto_reply_enabled:
    #     return {
    #         "should_reply": False,
    #         "reply_content": "",
    #         "reason": "自动回复已禁用"
    #     }
    
    try:
        # 1. 使用topk_api_module查找相似聊天记录，获取每条消息的下5条回复
        search_results = topk_api_module.search_messages_api(contact_name, current_message, k=50, n=1)
        
        if not search_results.get("success", False):
            return {
                "should_reply": False,
                "reply_content": "",
                "reason": f"搜索聊天记录失败: {search_results.get('error', '未知错误')}"
            }
        
        # 2. 构建对话历史
        conversation_history = []
        for result in search_results.get("results", [])[:100]:  # 只使用最近的100条记录
            content = result.get("content", "")
            # 过滤掉"[表情]"内容
            content = content.replace("[表情]", "")
            replies = result.get("next_messages", [])
            #if content:
                #conversation_history.append(content)
            if replies:
                # 遍历回复列表，只取前5条回复的content
                for reply in replies[:1]:
                    reply_content = reply.get("content", "")
                    # 过滤掉"[表情]"内容
                    reply_content = reply_content.replace("[表情]", "")
                    if reply_content:
                        conversation_history.append(reply_content)
        
        print(f"历史聊天记录：{conversation_history}")
        
        # 3. 构建提示词
        prompt = PROMPT_TEMPLATE.format(
            conversation_history="\n".join(conversation_history),
            current_message=current_message
        )
        
        # 4. 调用大模型API
        llm_response = call_llm_api(prompt)
        
        if not llm_response.get("success", False):
            return {
                "should_reply": False,
                "reply_content": "",
                "reason": f"调用大模型失败: {llm_response.get('error', '未知错误')}"
            }
        
        # 5. 解析大模型回复
        reply_content = llm_response.get("content", "")
        
        if not reply_content:
            return {
                "should_reply": False,
                "reply_content": "",
                "reason": "大模型未返回有效回复"
            }
        
        return {
            "should_reply": True,
            "reply_content": reply_content,
            "reason": "自动回复生成成功"
        }
        
    except Exception as e:
        return {
            "should_reply": False,
            "reply_content": "",
            "reason": f"自动回复过程中发生错误: {str(e)}"
        }

def call_llm_api(prompt: str) -> dict:
    """
    调用百炼大模型API
    
    Args:
        prompt (str): 提示词
        
    Returns:
        dict: 包含API调用结果的字典
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}"
        }
        
        # 百炼API请求格式
        payload = {
            "model": "qwen-plus",
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"max_tokens": 2000, "temperature": 0.3}
        }
        
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            if 'output' in result and 'text' in result['output']:
                # 尝试清洗可能存在的 markdown 标记
                clean_text = result['output']['text'].strip()
                return {
                    "success": True,
                    "content": clean_text.replace("```json", "").replace("```", "")
                }
            elif 'output' in result and 'choices' in result['output']:
                return {
                    "success": True,
                    "content": result['output']['choices'][0]['message']['content'].strip()
                }
            else:
                return {
                    "success": False,
                    "error": f"API返回格式错误: {result}"
                }
        else:
            return {
                "success": False,
                "error": f"API请求失败: {response.status_code}, {response.text}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"网络请求失败: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"API调用失败: {str(e)}"
        }

# 测试示例
if __name__ == "__main__":
    # 示例：测试与"OmoT"的自动回复
    test_message = "我是你爸"
    result = auto_reply("OmoT", test_message, "group")
    
    print(f"是否需要回复: {result['should_reply']}")
    print(f"回复内容: {result['reply_content']}")
    print(f"原因: {result['reason']}")
    print(result)