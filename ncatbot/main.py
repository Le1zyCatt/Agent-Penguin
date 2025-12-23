# ========= 导入必要模块 ==========
import asyncio
import json
import requests
import os
import time

from ncatbot.core import BotClient, GroupMessageEvent, PrivateMessageEvent
from ncatbot.core.event import Image, File
from ncatbot.core.event.message_segment import At, MessageArray
from ncatbot.utils import config

# ========== 配置 ==========
AGENT_PENGUIN_BASE_URL = "http://localhost:8000"

config.set_bot_uin("2401262719")
config.set_root("2812656625")
config.set_ws_uri("ws://localhost:3002")
config.set_ws_token("myj123")
config.set_webui_uri("http://localhost:6099")
config.set_webui_token("napcat")

# 机器人QQ号（需要与config.set_bot_uin保持一致）
BOT_UIN = "2401262719"

# ========== 创建 BotClient ==========
bot = BotClient()

# ========== 数据目录 ==========
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ========== 与 Agent-Penguin 通信 ==========
async def get_group_name(group_id: str):
    """获取群名称通过群ID"""
    try:
        group_info = await bot.api.get_group_info(group_id)
        return group_info.group_name
    except Exception as e:
        print(f"[NCatBot] 获取群信息失败 {group_id}: {e}")
        return f"群_{group_id}"  # 返回默认名称


def send_chat_message_to_agent(data: dict):
    print(
        "[NCatBot] 发送到 Agent-Penguin:\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
    )
    try:
        r = requests.post(
            f"{AGENT_PENGUIN_BASE_URL}/api/message/save",
            json=data,
            timeout=10,
        )
        return r.json() if r.ok else None
    except Exception as e:
        print("[NCatBot] Agent 通信异常:", e)
        return None


def download_temp_video(url: str, save_path: str):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://im.qq.com/"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(r.content)


# ================= 发送消息 API 封装 =================

async def send_reply(event, reply_content, message_type):
    """
    使用 ncatbot 正确 API 发送普通文本 (非引用).
    """
    msg = [{"type": "text", "data": {"text": reply_content}}]

    if message_type == "group":
        await bot.api.send_group_msg(group_id=event.group_id, message=msg)
    else:
        await bot.api.send_private_msg(user_id=event.user_id, message=msg)


# ================= 公共处理函数 =================

async def handle_text(event, message_type):
    # 检查是否被 @ 了
    is_at_me = check_if_at(event.message, BOT_UIN)

    texts = event.message.filter_text()
    if not texts:
        return

    text_content = "".join(t.text for t in texts)
    print(f"收到{message_type}文本:", text_content)
    print(f"是否被@了: {is_at_me}")

    # 为群聊消息添加群名称
    group_name = None
    if message_type == "group":
        group_name = await get_group_name(event.group_id)

    agent_data = {
        "post_type": "message",
        "message_type": message_type,
        "user_id": event.user_id,
        "group_id": getattr(event, "group_id", None),
        "group_name": group_name,  # 添加群名称
        "message_id": event.message_id,
        "raw_message": text_content,
        "is_at": is_at_me,  # 添加是否被@的信息
        "sender": {
            "user_id": event.user_id,
            "nickname": event.sender.nickname if event.sender else "Unknown",
        },
        "time": int(time.time()),
    }

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)

    if response and response.get("reply"):
        reply_content = response["reply"]
        print(f"发送自动回复: {reply_content}")
        await send_reply(event, reply_content, message_type)


def check_if_at(message_array: MessageArray, target_qq: str):
    """检测消息中是否包含 @ 某个用户"""
    for segment in message_array:
        if isinstance(segment, At):
            if segment.qq == target_qq or segment.qq == "all":  # 检查是否@了目标用户或全体成员
                return True
    return False


async def handle_images(event, message_type):
    images = event.message.filter(Image)
    if not images:
        return

    # 为群聊消息添加群名称
    group_name = None
    if message_type == "group":
        group_name = await get_group_name(event.group_id)

    for idx, img in enumerate(images, 1):
        try:
            image_path = await img.download(DATA_DIR)
            print("图片已保存:", image_path)
        except Exception as e:
            print("图片下载失败:", e)
            image_path = None

        agent_data = {
            "post_type": "message",
            "message_type": message_type,
            "user_id": event.user_id,
            "group_id": getattr(event, "group_id", None),
            "group_name": group_name,  # 添加群名称
            "message_id": event.message_id,
            "raw_message": f"[图片 {idx}]",
            "image_path": image_path,
            "time": int(time.time()),
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, send_chat_message_to_agent, agent_data
        )

        if response and response.get("reply"):
            reply_content = response["reply"]
            print(f"发送自动回复（图片）: {reply_content}")
            await send_reply(event, reply_content, message_type)


async def handle_files(event, message_type):
    files = event.message.filter(File)
    if not files:
        return

    # 为群聊消息添加群名称
    group_name = None
    if message_type == "group":
        group_name = await get_group_name(event.group_id)

    for file in files:
        try:
            file_path = await file.download(DATA_DIR)
            print("文件已保存:", file_path)

            agent_data = {
                "post_type": "message",
                "message_type": message_type,
                "user_id": event.user_id,
                "group_id": getattr(event, "group_id", None),
                "group_name": group_name,  # 添加群名称
                "message_id": event.message_id,
                "raw_message": f"[文件]{file.get_file_name()}",
                "file_path": file_path,
                "time": int(time.time()),
            }

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)

        except Exception as e:
            print("文件处理失败:", e)


async def handle_video_or_record(event, message_type):
    raw = event.raw_message or ""

    if "[CQ:video" not in raw:
        return

    print("检测到视频消息:", raw)

    import re
    import html

    m = re.search(r"url=([^,\]]+)", raw)
    if not m:
        print("未找到视频 url")
        return

    url = html.unescape(m.group(1))
    filename = f"video_{event.message_id}_{int(time.time())}.mp4"
    save_path = os.path.join(DATA_DIR, filename)

    # 为群聊消息添加群名称
    group_name = None
    if message_type == "group":
        group_name = await get_group_name(event.group_id)

    try:
        download_temp_video(url, save_path)
        print("视频已保存:", save_path)

        agent_data = {
            "post_type": "message",
            "message_type": message_type,
            "user_id": event.user_id,
            "group_id": getattr(event, "group_id", None),
            "group_name": group_name,  # 添加群名称
            "message_id": event.message_id,
            "raw_message": "[视频]",
            "video_path": save_path,
            "time": int(time.time()),
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_chat_message_to_agent, agent_data)

    except Exception as e:
        print("视频下载失败:", e)


# ================= 群聊 =================

@bot.on_group_message()
async def on_group_message(event: GroupMessageEvent):
    print("[NCatBot] 群聊:", event.raw_message)

    await handle_text(event, "group")
    await handle_images(event, "group")
    await handle_files(event, "group")
    await handle_video_or_record(event, "group")


# ================= 私聊 =================

@bot.on_private_message()
async def on_private_message(event: PrivateMessageEvent):
    print("[NCatBot] 私聊:", event.raw_message)

    await handle_text(event, "private")
    await handle_images(event, "private")
    await handle_files(event, "private")
    await handle_video_or_record(event, "private")


# ================= 启动 =================

if __name__ == "__main__":
    print("[NCatBot] 启动中")
    print("数据目录:", DATA_DIR)
    bot.run()
