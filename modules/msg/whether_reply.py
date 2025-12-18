# whether_reply.py
# 判断是否需要自动回复的模块

import requests
import json

import sys
import os

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))  # modules/msg/
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # Agent_Penguin/
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import config  # 导入配置模块

# 百炼API配置
LLM_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  # 百炼API地址
LLM_API_KEY = config.DASHSCOPE_API_KEY  # 使用配置文件中的API密钥

# 判断是否需要回复的提示词模板
PROMPT_TEMPLATE = """
请根据以下对话历史和当前消息，判断是否需要生成回复。

对话历史：
{conversation_history}

当前收到的消息：
{current_message}

判断规则：
1. 如果当前消息明确提到了你，或者你是被提及的对象，应该回复，返回"YES"
2. 如果当前消息是无关紧要的表情、符号、或者明显不需要回复的内容，可以不回复，返回"NO"
3. 如果当前消息是命令或请求，应该回复，返回"YES"
4. 如果当前消息是转发的信息、广告或与对话无关的内容，可以不回复，返回"NO"
5. 请注意这些消息是群聊的消息，你需要根据群聊的上下文判断是否需要回复。

请只返回"YES"或"NO"，不要有任何其他的多余词句。
"""

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
            "parameters": {"max_tokens": 10, "temperature": 0.1}  # 低温度确保结果稳定
        }
        
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
        
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

def whether_reply(contact_name: str, current_message: str, recent_history: list = None) -> dict:
    """
    判断是否需要自动回复的主函数
    
    Args:
        contact_name (str): 聊天对象姓名
        current_message (str): 当前用户输入的消息
        recent_history (list): 最近的聊天历史记录，格式为[{"sender": "name", "content": "message", "time": "timestamp"}]
        
    Returns:
        dict: 包含是否需要回复和原因的字典
    """
    try:
        # 构建对话历史字符串
        conversation_history = ""
        if recent_history and isinstance(recent_history, list):
            for msg in recent_history[-10:]:  # 只使用最近的10条历史记录
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                if sender and content:
                    conversation_history += f"{sender}: {content}\n"
        
        # 构建提示词
        prompt = PROMPT_TEMPLATE.format(
            conversation_history=conversation_history.strip(),
            current_message=current_message
        )
        
        # 调用大模型API
        llm_response = call_llm_api(prompt)
        
        if not llm_response.get("success", False):
            return {
                "should_reply": False,
                "reason": f"调用大模型失败: {llm_response.get('error', '未知错误')}"
            }
        
        # 解析大模型回复
        reply_content = llm_response.get("content", "").strip().upper()
        
        # 判断结果
        if reply_content == "YES":
            return {
                "should_reply": True,
                "reason": "模型判断需要回复"
            }
        elif reply_content == "NO":
            return {
                "should_reply": False,
                "reason": "模型判断不需要回复"
            }
        else:
            # 如果返回结果不是YES或NO，默认不回复
            return {
                "should_reply": False,
                "reason": f"模型返回无效结果: {reply_content}"
            }
            
    except Exception as e:
        return {
            "should_reply": False,
            "reason": f"判断过程中发生错误: {str(e)}"
        }

# 测试示例
if __name__ == "__main__":
    # 示例：测试是否需要回复
    test_contact = "OmoT"
    test_message = "好想要一个樱花妹啊"
    test_history = [
        {"sender": "OmoT", "content": "你好啊", "time": "2024-01-01 12:00:00"},
        # {"sender": "我", "content": "你好，有什么可以帮你的吗？", "time": "2024-01-01 12:01:00"},
        {"sender": "OmoT", "content": "好想要一个樱花妹啊", "time": "2024-01-01 12:02:00"}
    ]
    
    result = whether_reply(test_contact, test_message, test_history)
    
    print(f"是否需要回复: {result['should_reply']}")
    print(f"原因: {result['reason']}")