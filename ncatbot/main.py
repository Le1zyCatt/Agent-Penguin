# ncatbot/main.py
# ========= 导入必要模块 ==========
import asyncio
import json
import requests
from ncatbot.core import BotClient, PrivateMessage, GroupMessage
import threading
import time

# ========== 配置 ==========
AGENT_PENGUIN_BASE_URL = "http://localhost:8000"  # 修改为正确的端口

# ========== 创建 BotClient ==========
bot = BotClient()

# ========== 与Agent-Penguin通信的工具函数 ==========
def send_chat_message_to_agent(data: dict):
    """
    发送聊天消息到Agent-Penguin
    """
    try:
        # 保存消息到Agent-Penguin
        save_response = requests.post(f"{AGENT_PENGUIN_BASE_URL}/api/message/save", json=data, timeout=10)
        
        # 如果是需要自动回复的消息，则调用相关API
        if data.get("raw_message", "").startswith(("/", "!")):  # 假设命令以/或!开头
            # 这里可以根据消息内容调用不同的API
            if "search" in data.get("raw_message", ""):
                # 调用聊天记录搜索API
                query = data.get("raw_message", "").replace("/", "").replace("!", "")
                search_params = {
                    "contact": str(data.get("user_id")),
                    "query": query,
                    "k": 10
                }
                response = requests.get(f"{AGENT_PENGUIN_BASE_URL}/api/chat/search", params=search_params, timeout=10)
                if response.status_code == 200:
                    return response.json()
            elif "summarize" in data.get("raw_message", ""):
                # 调用消息总结API
                summary_data = {
                    "contact_id": str(data.get("user_id")),
                    "limit": 50,
                    "target_lang": "Chinese"
                }
                response = requests.post(f"{AGENT_PENGUIN_BASE_URL}/api/msg/summarize", data=summary_data, timeout=10)
                if response.status_code == 200:
                    return response.json()
        
        return {"reply": "消息已收到"}
    except Exception as e:
        print(f"[NCatBot] 发送到Agent-Penguin异常: {e}")
        return None

# ========= 注册回调函数 ==========
@bot.private_event()
async def on_private_message(msg: PrivateMessage):
    """
    处理私聊消息
    """
    print(f"[NCatBot] 收到私聊消息: {msg.raw_message} (来自: {msg.user_id})")
    
    # 构造发送给Agent-Penguin的数据格式
    agent_data = {
        "post_type": "message",
        "message_type": "private",
        "user_id": msg.user_id,
        "message_id": msg.message_id,
        "raw_message": msg.raw_message,
        "sender": {
            "user_id": msg.user_id,
            "nickname": msg.sender.nickname if msg.sender else "Unknown"
        },
        "time": int(time.time())
    }
    
    # 异步发送到Agent-Penguin处理
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
    
    # 根据响应内容发送回复
    if response and isinstance(response, dict):
        if "results" in response:  # 搜索结果
            reply_text = "找到相关内容:\n" + "\n".join([r.get("content", "") for r in response["results"][:3]])
            await bot.api.post_private_msg(user_id=msg.user_id, text=reply_text)
        elif "summary" in response:  # 总结结果
            reply_text = f"聊天记录总结:\n{response['summary']}"
            await bot.api.post_private_msg(user_id=msg.user_id, text=reply_text)
        elif "reply" in response:
            await bot.api.post_private_msg(user_id=msg.user_id, text=response["reply"])
    elif msg.raw_message == "测试":
        await bot.api.post_private_msg(user_id=msg.user_id, text="NcatBot 测试成功喵~")

@bot.group_event()
async def on_group_message(msg: GroupMessage):
    """
    处理群聊消息
    """
    print(f"[NCatBot] 收到群聊消息: {msg.raw_message} (来自群: {msg.group_id}, 发送者: {msg.user_id})")
    
    # 构造发送给Agent-Penguin的数据格式
    agent_data = {
        "post_type": "message",
        "message_type": "group",
        "group_id": msg.group_id,
        "user_id": msg.user_id,
        "message_id": msg.message_id,
        "raw_message": msg.raw_message,
        "sender": {
            "user_id": msg.user_id,
            "nickname": msg.sender.nickname if msg.sender else "Unknown"
        },
        "time": int(time.time())
    }
    
    # 异步发送到Agent-Penguin处理
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
    
    # 根据响应内容发送回复
    if response and isinstance(response, dict):
        if "results" in response:  # 搜索结果
            reply_text = "找到相关内容:\n" + "\n".join([r.get("content", "") for r in response["results"][:3]])
            await bot.api.post_group_msg(group_id=msg.group_id, text=reply_text)
        elif "summary" in response:  # 总结结果
            reply_text = f"聊天记录总结:\n{response['summary']}"
            await bot.api.post_group_msg(group_id=msg.group_id, text=reply_text)
        elif "reply" in response:
            await bot.api.post_group_msg(group_id=msg.group_id, text=response["reply"])

# ========== 启动 BotClient ==========
if __name__ == "__main__":
    print("[NCatBot] 正在启动...")
    print(f"[NCatBot] 将与Agent-Penguin在 {AGENT_PENGUIN_BASE_URL} 通信")
    bot.run()