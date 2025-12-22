# config.py
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 目录路径
DATA_DIR = os.path.join(BASE_DIR, "data")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
TEMP_DIR = os.path.join(DATA_DIR, "received_images")
FONT_PATH = os.path.join(DATA_DIR, "fonts", "simhei.ttf") # 确保你有这个字体

# 2. 向量数据库 (Project B)
# 注意：你的 vector_db_manager 可能默认读的是相对路径，这里我们显式指定绝对路径会更稳
VECTOR_DB_PATH = os.path.join(DATA_DIR, "chat_vector_db")
HISTORY_JSON_DIR = os.path.join(DATA_DIR, "server_history")

# 3. 阿里云百炼 API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-e4b45ce923944913baff2cc01cc0ab62") # 填入你的Key

# 4. PaddleOCR 服务配置
OCR_HOST = "0.0.0.0"
OCR_PORT = 8080
OCR_URL = f"http://localhost:{OCR_PORT}/ocr"

# 5. 自动回复配置
AUTO_REPLY_ENABLED = True  # 自动回复标志位，设置为True时启用自动回复
BOT_NAME = "耄仙人"
TOP_K = 30 # 从向量数据库中检索的Top K个文档
NEXT_N = 10 # 接下来的N条对话消息