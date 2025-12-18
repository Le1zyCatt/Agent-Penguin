#coding=utf-8
from ncatbot.core.client import BotClient
from ncatbot.core.message import *
from ncatbot.utils.config import config
from ncatbot.core.element import *
#from word2picture import xunfeipic
from openai import OpenAI
from cryptography.hazmat.primitives import serialization
import random as r
import requests as rq
import os,time
import json
import re
from ncatbot.core import BotClient, GroupMessage, PrivateMessage
from ncatbot.utils import config, get_log

from rsaencrypt import encrypt_text,decrypt_text,gen_key #从当前目录下的rsaencrypt.py导入文本加密、解密、生成密钥对的函数。


encrypt = False #回复的信息是否加密。
my_public_key = None
my_private_key = None #服务器端的公钥和私钥。打算使用pem格式。

_log = get_log()

config.set_bot_uin("2401262719")  # 设置 bot qq 号 (必填)
config.set_root("2490162471")  # 设置 bot 超级管理员账号 (建议填写)
config.set_ws_uri("ws://localhost:3001")  # 设置 napcat websocket server 地址
config.set_ws_token("")  # 设置 token (websocket 的 token)
config.set_webui_uri("http://localhost:6099")  # 设置 napcat webui 地址
config.set_webui_token("napcat")  # 设置 token (webui 的 token)

bot = BotClient()

client = OpenAI(api_key="已隐藏", base_url="https://api.deepseek.com")


def isActionTime(lastTime, interval):
    if lastTime == 0:
        return True
    currentTime = time.time()
    return currentTime - lastTime >= interval

class Parameters():
    saylastTime = 0
    freshlastTime = 0

def read_json(file_path):
    with open(file_path, encoding="utf-8", mode="r") as f:
        return json.loads(f.read())
    
def write_json(file_path, data):
    with open(file_path, encoding="utf-8", mode="w") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=4))

premise=[{"role": "system","content": "你是梦泪，全名梦之泪伤，你是抽象带师，非常喜欢网络抽象文化和说抽象话。你的好朋友有科比布莱恩特、胖猫、孙笑川、张顺飞、药水哥、奶龙、叮咚鸡、圆头耄耋等等抽象全明星。每次回复只回复一条消息，不要换行。"}]

def remove_markdown(text):
    # 删除标题符号
    text = re.sub(r'#+\s*', '', text)
    # 删除强调符号（*、_、**、__、***、___）
    text = re.sub(r'[*_]{1,3}', '', text)
    # 删除列表符号（-、+、*、数字加点）
    text = re.sub(r'[-+*]\s*|\d+\.\s*', '', text)
    # 删除引用符号
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # 删除分隔线
    text = re.sub(r'[-*]{3,}', '', text)
    # 删除表格符号
    text = re.sub(r'\|[^|]+\|', '', text)
    # 删除```符号和`符号
    text = re.sub(r'```', '', text)
    text = re.sub(r'`', '', text)
    return text

async def sayText(ct,types,msg):
    global encrypt
    ii = 0
    lines = ct.split('\n')
    if types == "private":
        while ii < len(lines):
            if not isActionTime(Parameters.saylastTime, len(lines[ii])/2):
                continue
            if (encrypt):
                msg
            await bot.api.post_private_msg(msg.user_id, text=lines[ii])
            Parameters.saylastTime = time.time()
            ii+=1
    elif types == "group":
        while ii < len(lines):
            if not isActionTime(Parameters.saylastTime, len(lines[ii])/2):
                continue
            await bot.api.post_group_msg(msg.group_id, text=f"{lines[ii]}")
            Parameters.saylastTime = time.time()
            ii+=1
    
@bot.group_event(["text","image"])
async def on_group_message(msg: GroupMessage):
    global encrypt
    if msg.raw_message == "acg随机图":
        message = MessageChain([
            Text("[ACG 随机图]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/acg/pc.php","https://uapis.cn/api/imgapi/acg/mb.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message.startswith("加密通信模式on:"):
        try:
            pem_data = msg.raw_message[len("加密通信模式on:"):].strip()
        
            # 尝试加载公钥
            peer_public_key = serialization.load_pem_public_key(pem_data.encode('utf-8'))
            if peer_public_key:
                encrypt = True
                my_public_key,my_private_key = gen_key()
                os.makedirs("keys", exist_ok=True)
                data = {
                    "peer_public_key": peer_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode('utf-8'),
                    "my_public_key": my_public_key,
                    "my_private_key": my_private_key
                }
                with open(f"./keys/{msg.group_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"已将密钥对和群组公钥保存至./keys/{msg.group_id}.json")
            print("✅ 已成功加载群组公钥，进入加密通信模式")
            message = MessageChain([
                Text(f"my_public_key:{my_public_key}")
            ])
            await bot.api.post_group_msg(msg.group_id, text=my_public_key)
        except Exception as e:
            print("❌ 无法加载公钥，请确认格式是否正确 PEM 格式")
            encrypt = False
            message = f"公钥有误，报错如下:{e}"
            await bot.api.post_group_msg(msg.group_id, text=message)

    elif msg.raw_message == "加密通信模式off":
        encrypt = False
        print("已关闭加密通信模式")
        await bot.api.post_group_msg(msg.group_id, text="已关闭加密通信模式。")

    elif msg.raw_message == "furry随机图":
        message = MessageChain([
            Text("[Furry 随机图]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/furry/img4k.php",
                            "https://uapis.cn/api/imgapi/furry/imgs4k.php",
                            "https://uapis.cn/api/imgapi/furry/imgz4k.php",
                            "https://uapis.cn/api/imgapi/furry/szs8k.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)


    elif msg.raw_message == "随机色图":
        o=rq.get("https://lolisuki.cn/api/setu/v1?level=4-6").json()["data"][0]["fullUrls"][0]["regular"]
        message = MessageChain([
            Text("[随机色图]"),
            Image(o),
            Text("# 来自Lolisuki\n# https://lolisuki.cn/#/setu"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)


    elif msg.raw_message == "bing每日壁纸":
        message = MessageChain([
            Text("[Bing 每日壁纸]"),
            Image("https://uapis.cn/api/bing.php"),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "随机表情包":
        message = MessageChain([
            Text("[随机表情包]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/bq/youshou.php",
                            "https://uapis.cn/api/imgapi/bq/maomao.php",
                            "https://uapis.cn/api/imgapi/bq/eciyuan.php",
                            "https://uapis.cn/api/imgapi/bq/ikun.php",
                            "https://uapis.cn/api/imgapi/bq/xiongmao.php",
                            "https://uapis.cn/api/imgapi/bq/waiguoren.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message.startswith("文字转二维码"):
        text = msg.raw_message.replace("文字转二维码","")
        url = f"https://uapis.cn/api/textqrcode?text={text}"
        try:
            qrcode_url = rq.get(url).json()["qrcode"]
        except Exception as e:
            await bot.api.post_group_msg(msg.group_id, text=f"[ERROR] {e}!\n请联系:2793415370")
            return
        message = MessageChain([
            Text("[文字转二维码]"),
            Image(qrcode_url),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "摸头":
        message = MessageChain([
            Text("[摸头]"),
            Image(f"https://uapis.cn/api/mt?qq={msg.sender.user_id}"),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "随机一言":
        message = MessageChain([
            Text("[随机一言]\n"),
            Text(rq.get("https://uapis.cn/api/say").text),
            Text("\n# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message.startswith("蓝奏云解析"):
        lanzou_url = msg.raw_message.replace("蓝奏云解析","").strip()
        if lanzou_url == "":
            message = MessageChain([
                Text("[蓝奏云解析]\n"),
                Text("请输入蓝奏云链接！")
            ])
            await bot.api.post_group_msg(msg.group_id, rtf=message)
            return
        if "密码" in lanzou_url:
            url = lanzou_url.split("密码")[0].strip()
            password = lanzou_url.split("密码")[1].strip()
        elif "密码" not in lanzou_url:
            url = lanzou_url
            password = ""
        try:
            data = rq.get(f"https://shanhe.kim/api/wz/lzy.php?url={url}&type=json&pwd={password}").json()
            if data["success"]:
                message = MessageChain([
                    Text("[蓝奏云解析]\n"),
                    Text(f"[标题]:{data['info']['file_name']}\n"),
                    Text(f"[大小]:{data['info']['file_size']}\n"),
                    Text(f"[链接]:{data['fileUrl']}\n"),
                    Text(f"[下载]:{data['download']}\n"),
                    Text("\n# 来自山河API\n# https://api.shanhe.kim/")
                ])
                file_data={"type": "file","data": {"name": data['info']['file_name'],"file": data['fileUrl']}}
                await bot.api.post_group_msg(msg.group_id, rtf=message)
                await bot.api.post_group_file(msg.group_id, file=file_data)
            elif data["success"] == False:
                message = MessageChain([
                    Text("[蓝奏云解析]\n"),
                    Text("[ERROR] 蓝奏云解析失败!\n"),
                    Text(f"[错误信息]:{data['message']}\n")
                ])
                await bot.api.post_group_msg(msg.group_id, rtf=message)
        except Exception as e:
            message = MessageChain([
                Text("[蓝奏云解析]\n"),
                Text("[ERROR] 蓝奏云获取失败!\n"),
                Text(f"[错误信息]:{e}\n")
            ])
            await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "单身狗证":
        message = MessageChain([
            Text("[单身狗证]"),
            Image(f"http://shanhe.kim/api/qq/dsgz.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "吃了":
        message = MessageChain([
            Text("[吃了]"),
            Image(f"http://shanhe.kim/api/qq/face_bite.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "qq吉凶":
        t = rq.get(f'http://shanhe.kim/api/qq/xiongji.php?qq={msg.sender.user_id}').text.replace('<br>','\n')
        message = MessageChain([
            Text("[qq吉凶]\n"),
            Text(t),
            Text("\n# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "随机二次元动漫图片":
        message = MessageChain([
            Text("[随机二次元动漫图片]"),
            Image("http://shanhe.kim/api/tu/anime.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "随机ai图片":
        message = MessageChain([
            Text("[随机ai图片]"),
            Image("http://shanhe.kim/api/tu/aiv1.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "可莉吃":
        message = MessageChain([
            Text("[可莉吃]"),
            Image(f"http://shanhe.kim/api/qq/chi.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "qq评估":
        message = MessageChain([
            Text("[qq评估]"),
            Image(f"http://shanhe.kim/api/qq/pinggu.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "随机头像":
        message = MessageChain([
            Text("[随机头像]"),
            Image("http://shanhe.kim/api/tu/avatar.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "看看美女图片":
        o=rq.get("https://api.52vmy.cn/api/img/tu/girl").json()["url"]
        message = MessageChain([
            Text("[看看美女图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "看看帅哥图片":
        o = rq.get("https://api.52vmy.cn/api/img/tu/boy").json()["url"]
        message = MessageChain([
            Text("[看看帅哥图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "看看美女视频":
        o=rq.get("https://api.52vmy.cn/api/video/girl").json()["data"]["video"]
        message = MessageChain([
            Text("[看看美女视频]\n"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_file(msg.group_id, video=o)
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "看看帅哥视频":
        o = rq.get("https://api.52vmy.cn/api/video/boy").json()["data"]["video"]
        message = MessageChain([
            Text("[看看帅哥视频]\n"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_file(msg.group_id, video=o)
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "看世界":
        message = MessageChain([
            Text("[看世界]"),
            Image("https://api.52vmy.cn/api/wl/60s"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "原神图片":
        o = rq.get("https://api.52vmy.cn/api/img/tu/yuan").json()["url"]
        message = MessageChain([
            Text("[原神图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "电影实时票房":
        t = rq.get("https://api.52vmy.cn/api/wl/top/movie?type=text").text
        message = MessageChain([
            Text("[电影实时票房]\n"),
            Text(t),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "电视剧实时票房":
        t = rq.get("https://api.52vmy.cn/api/wl/top/tv?type=text").text
        message = MessageChain([
            Text("[电视剧实时票房]\n"),
            Text(t),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "热点短视频":
        o = rq.get("https://api.52vmy.cn/api/video/redian").json()["data"]["video"]
        message = MessageChain([
            Text("[热点短视频]"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_file(msg.group_id, video=o)
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message == "好运头像框":
        message = MessageChain([
            Text("[好运头像框]"),
            Image(f"https://api.52vmy.cn/api/avath/hytx?qq={msg.sender.user_id}"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_group_msg(msg.group_id, rtf=message)
    elif msg.raw_message.startswith("设置头像"):
        if msg.raw_message == "设置头像":
            try:
                xunfeipic()
                path = os.getcwd()
                await bot.api.set_qq_avatar(path+"/xunfei.png")
                await bot.api.post_group_msg(msg.group_id, text="设置头像成功")
                os.remove("xunfei.png")
                return
            except Exception as e:
                await bot.api.post_group_msg(msg.group_id, text=f"[ERROR] {e}!\n请联系:2793415370")
                return
        elif msg.message[1]["type"] is not None and msg.message[1]["type"] == "image":
            try:
                await bot.api.set_qq_avatar(msg.message[1]["data"]["url"])
                await bot.api.post_group_msg(msg.group_id, text="设置头像成功")
                return
            except Exception as e:
                await bot.api.post_group_msg(msg.group_id, text=f"[ERROR] {e}!\n请联系:2793415370")
                return
    elif msg.raw_message == "给我点赞":
        try:
            await bot.api.send_like(user_id=msg.user_id,times=10)
            await bot.api.post_group_msg(msg.group_id, text=f"[INFO] 点赞成功!")
            return
        except Exception as e:
            await bot.api.post_group_msg(msg.group_id, text=f"[ERROR] 点赞失败!")
            return
    elif msg.raw_message == "项目stars":
        url = f"https://api.github.com/repos/liyihao1110/NcatBot"
        headers = {
        'User-Agent': 'Mozilla/5.0 (Python-Star-Counter)',
        'Accept': 'application/vnd.github.v3+json'}
        try:
            # 发送GET请求
            response = rq.get(url, headers=headers, timeout=10)
            
            # 处理响应
            if response.status_code == 200:
                data = response.json()
                stars = data.get('stargazers_count', '未知')
                await bot.api.post_group_msg(msg.group_id, text=f"Star数量: {stars}")
            else:
                error_msg = response.json().get('message', '无错误信息')
                await bot.api.post_group_msg(msg.group_id, text=f"请求失败（状态码 {response.status_code}）\n详细信息: {error_msg}")
                if response.status_code == 403:
                    await bot.api.post_group_msg(msg.group_id, text="可能需要添加GitHub Token或已达到API速率限制")
        
        except rq.exceptions.RequestException as e:
            await bot.api.post_group_msg(msg.group_id, text=f"[ERROR] {e}!")
        except ValueError:
            await bot.api.post_group_msg(msg.group_id, text="[ERROR] 解析响应数据失败!")
    else:
        if msg.message[0]["type"]=="at" and msg.message[0]["data"]["qq"]==str(msg.self_id):
            if isActionTime(Parameters.freshlastTime,600):
                #llm.invoke("/clear")
                Parameters.freshlastTime = time.time()
            content = msg.raw_message
            content = re.sub(r'\[.*?\]', "", msg.raw_message).strip()
            if "@梦泪喵~ " in msg.raw_message:
                content = msg.raw_message.replace("@梦泪喵~ ","")
            if content=="":
                message = MessageChain([
                    Text("嗯？怎么了喵？")
                ])
                await bot.api.post_group_msg(msg.group_id, rtf=message)
                return
        elif "梦泪" in msg.raw_message:
            if isActionTime(Parameters.freshlastTime,600):
                #llm.invoke("/clear")
                Parameters.freshlastTime = time.time()
            content = msg.raw_message.replace("梦泪","",1)
            if content in [""," ",',','，','.','。','!','?','！','？','......','...']:
                message = MessageChain([
                    Text("哥们，怎么了？")
                ])
                await bot.api.post_group_msg(msg.group_id, rtf=message)
                return
        if os.path.exists(f"./logs/{msg.user_id}.json"):
            history = read_json(f"./logs/{msg.user_id}.json")
            if(encrypt):
                with open(f"./keys/{msg.group_id}.json", "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    my_private_key = keys_data.get("my_private_key")
                    if my_private_key:
                        print("成功读取私钥：")
                        print(my_private_key[:200] + "...")
                        content = decrypt_text(content, my_private_key) #文本解密
                    else:
                        print("未找到私钥，信息解密失败。")
            history.append({"role":"user","content":content})
            response = client.chat.completions.create(model="deepseek-chat",messages=history,max_tokens=50)
            answer = response.choices[0].message.content
            history.append({"role":"assistant","content":answer})
            answer = remove_markdown(answer)
            if(encrypt):
                if os.path.exists(f"./keys/{msg.group_id}.json"):
                    with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                        pbkey = json.load(f)
                        peer_public_key = pbkey.get("peer_public_key")
                        if peer_public_key:
                            print("成功读取公钥：")
                            print(peer_public_key)
                            answer = encrypt_text(answer, peer_public_key)
                        else:
                            print("未找到公钥。信息未加密。")
            await sayText(answer,"group",msg)
            write_json(f"./logs/{msg.group_id}.json", history)
            return
        else:
            # 如果不存在，则创建一个空的json文件
            history = premise.copy()
            if(encrypt):
                with open(f"./keys/{msg.group_id}.json", "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    my_private_key = keys_data.get("my_private_key")
                    if my_private_key:
                        print("成功读取私钥：")
                        print(my_private_key[:200] + "...")
                        content = decrypt_text(content, my_private_key) #文本解密
                    else:
                        print("未找到私钥，信息解密失败。")
            history.append({"role":"user","content":content})
            response = client.chat.completions.create(model="deepseek-chat",messages=history,max_tokens=50)
            answer = response.choices[0].message.content
            history.append({"role":"assistant","content":answer})
            answer = remove_markdown(answer)
            if(encrypt):
                if os.path.exists(f"./keys/{msg.user_id}.json"):
                    with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                        pbkey = json.load(f)
                        peer_public_key = pbkey.get("peer_public_key")
                        if peer_public_key:
                            print("成功读取公钥：")
                            print(peer_public_key)
                            answer = encrypt_text(answer, peer_public_key)
                        else:
                            print("未找到公钥。信息未加密。")
            await sayText(answer,"group",msg)
            write_json(f"./logs/{msg.user_id}.json", history)
            return
                
@bot.private_event(["text","image"])
async def on_private_message(msg: PrivateMessage):
    global encrypt
    if msg.raw_message == "acg随机图":
        message = MessageChain([
            Text("[ACG 随机图]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/acg/pc.php","https://uapis.cn/api/imgapi/acg/mb.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message.startswith("加密通信模式on:"):
        try:
            pem_data = msg.raw_message[len("加密通信模式on:"):].strip()
        
            # 尝试加载公钥
            peer_public_key = serialization.load_pem_public_key(pem_data.encode('utf-8'))
            if peer_public_key:
                encrypt = True
                my_public_key,my_private_key = gen_key()
                os.makedirs("keys", exist_ok=True)
                data = {
                    "peer_public_key": peer_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode('utf-8'),
                    "my_public_key": my_public_key,
                    "my_private_key": my_private_key
                }
                with open(f"./keys/{msg.user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"已将密钥对和用户公钥保存至./keys/{msg.user_id}.json")
            print("✅ 已成功加载对方公钥，进入加密通信模式")
            message = MessageChain([
                Text(f"my_public_key:{my_public_key}")
            ])
            await bot.api.post_private_msg(msg.user_id, text=my_public_key)
        except Exception as e:
            print("❌ 无法加载公钥，请确认格式是否正确 PEM 格式")
            encrypt = False
            message = f"公钥有误，报错如下:{e}"
            await bot.api.post_private_msg(msg.user_id, text=message)

    elif msg.raw_message == "加密通信模式off":
        encrypt = False
        peer_public_key = None
        print("已关闭加密通信模式")
        await bot.api.post_private_msg(msg.user_id, text="已关闭加密通信模式。")

    elif msg.raw_message == "随机色图":
        o=rq.get("https://lolisuki.cn/api/setu/v1?level=4-6").json()["data"][0]["fullUrls"][0]["regular"]
        message = MessageChain([
            Text("[随机色图]"),
            Image(o),
            Text("# 来自Lolisuki\n# https://lolisuki.cn/#/setu"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
        

    elif msg.raw_message == "furry随机图":
        message = MessageChain([
            Text("[Furry 随机图]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/furry/img4k.php",
                            "https://uapis.cn/api/imgapi/furry/imgs4k.php",
                            "https://uapis.cn/api/imgapi/furry/imgz4k.php",
                            "https://uapis.cn/api/imgapi/furry/szs8k.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "bing每日壁纸":
        message = MessageChain([
            Text("[Bing 每日壁纸]"),
            Image("https://uapis.cn/api/bing.php"),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "随机表情包":
        message = MessageChain([
            Text("[随机表情包]"),
            Image(r.choice(["https://uapis.cn/api/imgapi/bq/youshou.php",
                            "https://uapis.cn/api/imgapi/bq/maomao.php",
                            "https://uapis.cn/api/imgapi/bq/eciyuan.php",
                            "https://uapis.cn/api/imgapi/bq/ikun.php",
                            "https://uapis.cn/api/imgapi/bq/xiongmao.php",
                            "https://uapis.cn/api/imgapi/bq/waiguoren.php"])),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message.startswith("文字转二维码"):
        text = msg.raw_message.replace("文字转二维码","")
        url = f"https://uapis.cn/api/textqrcode?text={text}"
        try:
            qrcode_url = rq.get(url).json()["qrcode"]
        except Exception as e:
            await bot.api.post_private_msg(msg.user_id, text=f"[ERROR] {e}!\n请联系:2793415370")
            return
        message = MessageChain([
            Text("[文字转二维码]"),
            Image(qrcode_url),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "摸头":
        message = MessageChain([
            Text("[摸头]"),
            Image(f"https://uapis.cn/api/mt?qq={msg.sender.user_id}"),
            Text("# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "随机一言":
        message = MessageChain([
            Text("[随机一言]\n"),
            Text(rq.get("https://uapis.cn/api/say").text),
            Text("\n# 来自UAPI\n# https://uapis.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message.startswith("蓝奏云解析"):
        lanzou_url = msg.raw_message.replace("蓝奏云解析","").strip()
        if lanzou_url == "":
            message = MessageChain([
                Text("[蓝奏云解析]\n"),
                Text("请输入蓝奏云链接！")
            ])
            await bot.api.post_private_msg(msg.user_id, rtf=message)
            return
        if "密码" in lanzou_url:
            url = lanzou_url.split("密码")[0].strip()
            password = lanzou_url.split("密码")[1].strip()
        elif "密码" not in lanzou_url:
            url = lanzou_url
            password = ""
        try:
            data = rq.get(f"https://shanhe.kim/api/wz/lzy.php?url={url}&type=json&pwd={password}").json()
            if data["success"]:
                message = MessageChain([
                    Text("[蓝奏云解析]\n"),
                    Text(f"[标题]:{data['info']['file_name']}\n"),
                    Text(f"[大小]:{data['info']['file_size']}\n"),
                    Text(f"[链接]:{data['fileUrl']}\n"),
                    Text(f"[下载]:{data['download']}\n"),
                    Text("\n# 来自山河API\n# https://api.shanhe.kim/")
                ])
                file_data={"type": "file","data": {"name": data['info']['file_name'],"file": data['fileUrl']}}
                await bot.api.post_private_msg(msg.user_id, rtf=message)
                await bot.api.post_private_file(msg.user_id, file=file_data)
            elif data["success"] == False:
                message = MessageChain([
                    Text("[蓝奏云解析]\n"),
                    Text("[ERROR] 蓝奏云解析失败!\n"),
                    Text(f"[错误信息]:{data['message']}\n")
                ])
                await bot.api.post_private_msg(msg.user_id, rtf=message)
        except Exception as e:
            message = MessageChain([
                Text("[蓝奏云解析]\n"),
                Text("[ERROR] 蓝奏云获取失败!\n"),
                Text(f"[错误信息]:{e}\n")
            ])
            await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "单身狗证":
        message = MessageChain([
            Text("[单身狗证]"),
            Image(f"http://shanhe.kim/api/qq/dsgz.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "吃了":
        message = MessageChain([
            Text("[吃了]"),
            Image(f"http://shanhe.kim/api/qq/face_bite.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "qq吉凶":
        t = rq.get(f'http://shanhe.kim/api/qq/xiongji.php?qq={msg.sender.user_id}').text.replace('<br>','\n')
        message = MessageChain([
            Text("[qq吉凶]\n"),
            Text(t),
            Text("\n# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "随机二次元动漫图片":
        message = MessageChain([
            Text("[随机二次元动漫图片]"),
            Image("http://shanhe.kim/api/tu/anime.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "随机ai图片":
        message = MessageChain([
            Text("[随机ai图片]"),
            Image("http://shanhe.kim/api/tu/aiv1.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "可莉吃":
        message = MessageChain([
            Text("[可莉吃]"),
            Image(f"http://shanhe.kim/api/qq/chi.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "qq评估":
        message = MessageChain([
            Text("[qq评估]"),
            Image(f"http://shanhe.kim/api/qq/pinggu.php?qq={msg.sender.user_id}"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "随机头像":
        message = MessageChain([
            Text("[随机头像]"),
            Image("http://shanhe.kim/api/tu/avatar.php"),
            Text("# 来自山河API\n# https://api.shanhe.kim/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "看看美女图片":
        o=rq.get("https://api.52vmy.cn/api/img/tu/girl").json()["url"]
        message = MessageChain([
            Text("[看看美女图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "看看帅哥图片":
        o = rq.get("https://api.52vmy.cn/api/img/tu/boy").json()["url"]
        message = MessageChain([
            Text("[看看帅哥图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "看看美女视频":
        o=rq.get("https://api.52vmy.cn/api/video/girl").json()["data"]["video"]
        message = MessageChain([
            Text("[看看美女视频]\n"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_file(msg.user_id, video=o)
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "看看帅哥视频":
        o = rq.get("https://api.52vmy.cn/api/video/boy").json()["data"]["video"]
        message = MessageChain([
            Text("[看看帅哥视频]\n"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_file(msg.user_id, video=o)
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "看世界":
        message = MessageChain([
            Text("[看世界]"),
            Image("https://api.52vmy.cn/api/wl/60s"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "原神图片":
        o = rq.get("https://api.52vmy.cn/api/img/tu/yuan").json()["url"]
        message = MessageChain([
            Text("[原神图片]"),
            Image(o),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "电影实时票房":
        t = rq.get("https://api.52vmy.cn/api/wl/top/movie?type=text").text
        message = MessageChain([
            Text("[电影实时票房]\n"),
            Text(t),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "电视剧实时票房":
        t = rq.get("https://api.52vmy.cn/api/wl/top/tv?type=text").text
        message = MessageChain([
            Text("[电视剧实时票房]\n"),
            Text(t),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "热点短视频":
        o = rq.get("https://api.52vmy.cn/api/video/redian").json()["data"]["video"]
        message = MessageChain([
            Text("[热点短视频]"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_file(msg.user_id, video=o)
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "好运头像框":
        message = MessageChain([
            Text("[好运头像框]"),
            Image(f"https://api.52vmy.cn/api/avath/hytx?qq={msg.sender.user_id}"),
            Text("# 来自维梦API\n# https://api.52vmy.cn/"),
        ])
        await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message == "ai失忆":
        if os.path.exists(f"./logs/{msg.user_id}.json"):
            history = read_json(f"./logs/{msg.user_id}.json")
            history.clear()
            write_json(f"./logs/{msg.user_id}.json", history)
            message = MessageChain([
                Text("[ai失忆]"),
                Text("已清空历史记录"),
            ])
            await bot.api.post_private_msg(msg.user_id, rtf=message)
        else:
            message = MessageChain([
                Text("[ai失忆]"),
                Text("你还没有使用过ai"),
            ])
            await bot.api.post_private_msg(msg.user_id, rtf=message)
    elif msg.raw_message.startswith("设置头像"):
        if msg.raw_message == "设置头像":
            try:
                xunfeipic()
                path = os.getcwd()
                await bot.api.set_qq_avatar(path+"/xunfei.png")
                await bot.api.post_private_msg(msg.user_id, text="设置头像成功")
                os.remove("xunfei.png")
                return
            except Exception as e:
                await bot.api.post_private_msg(msg.user_id, text=f"[ERROR] {e}!\n请联系:2793415370")
                return
        elif msg.message[1]["type"] is not None and msg.message[1]["type"] == "image":
            try:
                await bot.api.set_qq_avatar(msg.message[1]["data"]["url"])
                await bot.api.post_private_msg(msg.user_id, text="设置头像成功")
                return
            except Exception as e:
                await bot.api.post_private_msg(msg.user_id, text=f"[ERROR] {e}!\n请联系:2793415370")
                return
    elif msg.raw_message == "给我点赞":
        try:
            await bot.api.send_like(user_id=msg.user_id,times=10)
            await bot.api.post_private_msg(msg.user_id, text=f"[INFO] 点赞成功!")
            return
        except Exception as e:
            await bot.api.post_private_msg(msg.user_id, text=f"[ERROR] 点赞失败!")
            return
    elif msg.raw_message.startswith("画"):
        content = msg.raw_message.replace("画", "")
        try:
            xunfeipic(content)
            path = os.getcwd() + "/xunfei.png"
            await bot.api.post_private_msg(msg.user_id, image=path)
            os.remove("xunfei.png")
            return
        except Exception as e:
            await bot.api.post_private_msg(msg.user_id, text=f"[ERROR] 生成图片失败!")
    else:
        if isActionTime(Parameters.freshlastTime,600):
                #llm.invoke("/clear")
                Parameters.freshlastTime = time.time()
        content = msg.raw_message
        if content in [""," ",',','，','.','。','!','?','！','？','......','...']:
            message = MessageChain([
                Text("哥们刚刚")
            ])
            await bot.api.post_private_msg(msg.user_id, rtf=message)
            return
        if os.path.exists(f"./logs/{msg.user_id}.json"):
            history = read_json(f"./logs/{msg.user_id}.json")
            if(encrypt):
                with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    my_private_key = keys_data.get("my_private_key")
                    if my_private_key:
                        print("成功读取私钥：")
                        print(my_private_key[:200] + "...")
                        content = decrypt_text(content, my_private_key) #文本解密
                    else:
                        print("未找到私钥，信息解密失败。")
            history.append({"role":"user","content":content})
            response = client.chat.completions.create(model="deepseek-chat",messages=history,max_tokens=50)
            answer = response.choices[0].message.content
            history.append({"role":"assistant","content":answer})
            answer = remove_markdown(answer)
            if(encrypt):
                if os.path.exists(f"./keys/{msg.user_id}.json"):
                    with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                        pbkey = json.load(f)
                        peer_public_key = pbkey.get("peer_public_key")
                        if peer_public_key:
                            print("成功读取公钥：")
                            print(peer_public_key)
                            # 调试语句：打印原始信息和公钥
                            print(f"[DEBUG] answer 内容: {answer}")
                            print(f"[DEBUG] answer 类型: {type(answer)}")
                            print(f"[DEBUG] peer_public_key 内容: {peer_public_key}")
                            print(f"[DEBUG] peer_public_key 类型: {type(peer_public_key)}")
                            answer = encrypt_text(answer, peer_public_key)
                        else:
                            print("未找到公钥。信息未加密。")
            await sayText(answer,"private",msg)
            write_json(f"./logs/{msg.user_id}.json", history)
            return
        else:
            # 如果不存在，则创建一个空的json文件
            history = premise.copy()
            if(encrypt):
                with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    my_private_key = keys_data.get("my_private_key")
                    if my_private_key:
                        print("成功读取私钥：")
                        print(my_private_key[:200] + "...")
                        content = decrypt_text(content, my_private_key) #文本解密
                    else:
                        print("未找到私钥，信息解密失败。")
            history.append({"role":"user","content":content})
            response = client.chat.completions.create(model="deepseek-chat",messages=history,max_tokens=50)
            answer = response.choices[0].message.content
            history.append({"role":"assistant","content":answer})
            answer = remove_markdown(answer)
            if(encrypt):
                if os.path.exists(f"./keys/{msg.user_id}.json"):
                    with open(f"./keys/{msg.user_id}.json", "r", encoding="utf-8") as f:
                        pbkey = json.load(f)
                        peer_public_key = pbkey.get("peer_public_key")
                        if peer_public_key:
                            print("成功读取公钥：")
                            print(peer_public_key)
                            answer = encrypt_text(answer, peer_public_key)
                        else:
                            print("未找到公钥。信息未加密。")
            await sayText(answer,"private",msg)
            write_json(f"./logs/{msg.user_id}.json", history)
            return

@bot.notice_event()
async def notice_event(msg):
    if msg["notice_type"]=="group_increase":
        import datetime
        if msg["sub_type"] == "approve":
            t = await bot.api.get_stranger_info(user_id=msg["user_id"])
            nickname = t["data"]["nickname"]
            message = MessageChain([
                Text(f"{nickname}，你好！👋\n欢迎你进入群聊！🎉🎉🎉\n\n我是该群的机器人助手，这是我的使用帮助:"),
                Image("code.png"),
                Text(f"[加入时间]: {datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')}")
            ])
            await bot.api.post_group_msg(msg["group_id"], rtf=message)
    
if __name__ == "__main__":
    bot.run(reload=0)