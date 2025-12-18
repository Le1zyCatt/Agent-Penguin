# ncatbot/main.py
# ========= 导入必要模块 ==========
import asyncio
import json
import requests
import os
import time
from ncatbot.core import BotClient, GroupMessageEvent, PrivateMessageEvent
from ncatbot.core.event import Text, Image, File
from ncatbot.utils import config, get_log

# ========== 配置 ==========
AGENT_PENGUIN_BASE_URL = "http://localhost:8000"  # 修改为正确的端口

config.set_bot_uin("2401262719")  # 设置 bot qq 号 (必填)
config.set_root("2490162471")  # 设置 bot 超级管理员账号 (建议填写)
config.set_ws_uri("ws://localhost:3001")  # 设置 napcat websocket server 地址
config.set_ws_token("")  # 设置 token (websocket 的 token)
config.set_webui_uri("http://localhost:6099")  # 设置 napcat webui 地址
config.set_webui_token("napcat")  # 设置 token (webui 的 token)
# ========== 创建 BotClient ==========
bot = BotClient()

# 确保data目录存在
os.makedirs("./data", exist_ok=True)

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
@bot.on_group_message()
async def on_group_message(event: GroupMessageEvent):
    """
    处理群聊消息
    """
    print(f"[NCatBot] 收到群聊消息: {event.raw_message} (来自群: {event.group_id}, 发送者: {event.user_id})")
    
    # 获取消息内容
    message = event.message
    
    # 处理文本消息
    texts = message.filter_text()
    if texts:
        text_content = "".join([t.data["text"] for t in texts])
        print(f"收到群文本消息: {text_content}")
        
        # 构造发送给Agent-Penguin的数据格式
        agent_data = {
            "post_type": "message",
            "message_type": "group",
            "group_id": event.group_id,
            "user_id": event.user_id,
            "message_id": event.message_id,
            "raw_message": text_content,
            "sender": {
                "user_id": event.user_id,
                "nickname": event.sender.nickname if event.sender else "Unknown"
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
                await event.reply(text=reply_text)
            elif "summary" in response:  # 总结结果
                reply_text = f"聊天记录总结:\n{response['summary']}"
                await event.reply(text=reply_text)
            elif "reply" in response:
                await event.reply(text=response["reply"])
        
        # 回复文本消息
        await event.reply(text=f"收到你的消息: {text_content}")
    
    # 处理图片消息
    images = message.filter_image()
    if images:
        print(f"收到群图片消息，共 {len(images)} 张图片")
        
        # 为每张图片构造发送给Agent-Penguin的数据格式
        for i, img in enumerate(images):
            agent_data = {
                "post_type": "message",
                "message_type": "group",
                "group_id": event.group_id,
                "user_id": event.user_id,
                "message_id": event.message_id,
                "raw_message": f"[图片{i+1}]",
                "image_path": img.file,  # 图片路径
                "sender": {
                    "user_id": event.user_id,
                    "nickname": event.sender.nickname if event.sender else "Unknown"
                },
                "time": int(time.time())
            }
            
            # 异步发送到Agent-Penguin处理
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
        
        # 回复图片消息
        await event.reply(text="收到图片!")
    
    # 处理文件消息
    files = message.filter(File)
    if files:
        print(f"收到群文件消息，共 {len(files)} 个文件")
        
        # 下载文件并为每个文件构造发送给Agent-Penguin的数据格式
        for file in files:
            try:
                file_path = await file.download("./data")
                print(f"文件已保存到: {file_path}")
                
                # 构造发送给Agent-Penguin的数据格式
                agent_data = {
                    "post_type": "message",
                    "message_type": "group",
                    "group_id": event.group_id,
                    "user_id": event.user_id,
                    "message_id": event.message_id,
                    "raw_message": f"[文件]{file.get_file_name()}",
                    "file_path": file_path,  # 文件路径
                    "sender": {
                        "user_id": event.user_id,
                        "nickname": event.sender.nickname if event.sender else "Unknown"
                    },
                    "time": int(time.time())
                }
                
                # 异步发送到Agent-Penguin处理
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
                
                # 回复文件消息
                await event.reply(text=f"收到文件: {file.get_file_name()}")
            except Exception as e:
                print(f"文件下载失败: {e}")
                await event.reply(text="文件下载失败")

@bot.on_private_message()
async def on_private_message(event: PrivateMessageEvent):
    """
    处理私聊消息
    """
    print(f"[NCatBot] 收到私聊消息: {event.raw_message} (来自: {event.user_id})")
    
    # 获取消息内容
    message = event.message
    
    # 处理文本消息
    texts = message.filter_text()
    if texts:
        text_content = "".join([t.data["text"] for t in texts])
        print(f"收到私聊文本消息: {text_content}")
        
        # 构造发送给Agent-Penguin的数据格式
        agent_data = {
            "post_type": "message",
            "message_type": "private",
            "user_id": event.user_id,
            "message_id": event.message_id,
            "raw_message": text_content,
            "sender": {
                "user_id": event.user_id,
                "nickname": event.sender.nickname if event.sender else "Unknown"
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
                await event.reply(text=reply_text)
            elif "summary" in response:  # 总结结果
                reply_text = f"聊天记录总结:\n{response['summary']}"
                await event.reply(text=reply_text)
            elif "reply" in response:
                await event.reply(text=response["reply"])
        
        # 回复文本消息
        await event.reply(text=f"收到你的私聊消息: {text_content}")
    
    # 处理图片消息
    images = message.filter_image()
    if images:
        print(f"收到私聊图片消息，共 {len(images)} 张图片")
        
        # 为每张图片构造发送给Agent-Penguin的数据格式
        for i, img in enumerate(images):
            agent_data = {
                "post_type": "message",
                "message_type": "private",
                "user_id": event.user_id,
                "message_id": event.message_id,
                "raw_message": f"[图片{i+1}]",
                "image_path": img.file,  # 图片路径
                "sender": {
                    "user_id": event.user_id,
                    "nickname": event.sender.nickname if event.sender else "Unknown"
                },
                "time": int(time.time())
            }
            
            # 异步发送到Agent-Penguin处理
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
        
        # 回复图片消息
        await event.reply(text="收到图片!")
    
    # 处理文件消息
    files = message.filter(File)
    if files:
        print(f"收到私聊文件消息，共 {len(files)} 个文件")
        
        # 下载文件并为每个文件构造发送给Agent-Penguin的数据格式
        for file in files:
            try:
                file_path = await file.download("./data")
                print(f"文件已保存到: {file_path}")
                
                # 构造发送给Agent-Penguin的数据格式
                agent_data = {
                    "post_type": "message",
                    "message_type": "private",
                    "user_id": event.user_id,
                    "message_id": event.message_id,
                    "raw_message": f"[文件]{file.get_file_name()}",
                    "file_path": file_path,  # 文件路径
                    "sender": {
                        "user_id": event.user_id,
                        "nickname": event.sender.nickname if event.sender else "Unknown"
                    },
                    "time": int(time.time())
                }
                
                # 异步发送到Agent-Penguin处理
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)
                
                # 回复文件消息
                await event.reply(text=f"收到文件: {file.get_file_name()}")
            except Exception as e:
                print(f"文件下载失败: {e}")
                await event.reply(text="文件下载失败")

# ========== 启动 BotClient ==========
if __name__ == "__main__":
    print("[NCatBot] 正在启动...")
    print(f"[NCatBot] 将与Agent-Penguin在 {AGENT_PENGUIN_BASE_URL} 通信")
    bot.run()