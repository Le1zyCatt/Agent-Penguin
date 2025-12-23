import os
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 配置
INPUT_HTML = "data/chat_history/nmbz.html"           # 原始 HTML 文件路径
OUTPUT_HTML = "data/chat_history/nmbz_full.html"     # 完整 HTML 保存路径
OUTPUT_JSON_DIR = "data/history_json"     # JSON 保存目录
ME_NAME = "懒猫"                   # 根据右侧判断自己消息的名字
SCROLL_PAUSE = 0.5                 # 每次滚动等待时间

# 创建所有必要的目录
os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)  # 创建 data/chat_history 目录
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)               # 创建 data/history_json 目录

# --- Step 1: 用 Selenium 加载完整 HTML ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # 可去掉，显示浏览器
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--log-level=3")

driver = webdriver.Chrome(options=chrome_options)
driver.get(f"file:///{os.path.abspath(INPUT_HTML)}")

# 自动滚动加载全部消息
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)  # 等待 JS 渲染
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        # 再多滚动几次确保懒加载
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        break
    last_height = new_height


# 保存完整 HTML
full_html = driver.page_source
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(full_html)

driver.quit()
print(f"[INFO] 完整 HTML 已保存：{OUTPUT_HTML}")

# --- Step 2: 解析完整 HTML ---
with open(OUTPUT_HTML, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

messages = []
for msg in soup.select("div.msg.chat"):
    msgid = msg.get("msgid")
    msgtype = msg.get("msgtype")
    content_span = msg.select_one("span.msg-text")
    content = content_span.get_text(strip=True) if content_span else ""

    # 发送者
    dsp_span = msg.select_one("span.dspname")
    sender = dsp_span.get_text(strip=True) if dsp_span else (ME_NAME if "right" in msg.get("class", []) else "未知")

    # 发送时间
    time_div = msg.select_one("div.nt-box")
    time_text = time_div.get_text(strip=True).replace(sender, "").strip() if time_div else ""

    messages.append({
        "id": msgid,
        "name": sender,
        "time": time_text,
        "text": content,
        "msgtype": msgtype
    })

# 按 msgid 排序
messages.sort(key=lambda x: int(x["id"]) if x["id"] is not None else 0)

# 用对方名字命名文件
if messages:
    other_name = [m["name"] for m in messages if m["name"] != ME_NAME and m["name"] != "未知"]
    if other_name:
        filename = f"{other_name[0]}.json"
    else:
        filename = "unknown.json"

    with open(os.path.join(OUTPUT_JSON_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] JSON 已保存：{os.path.join(OUTPUT_JSON_DIR, filename)}")
else:
    print("[WARNING] 未找到任何消息，JSON 文件未创建")
    filename = "unknown.json"  # 仅为最后的打印语句设置默认值