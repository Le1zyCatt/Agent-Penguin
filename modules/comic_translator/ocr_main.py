from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import zipfile
import os
import io
import subprocess
import sys
import time
import threading
import json


from utils.paddle_ocr import image_to_base64, ocr_image, extract_text
from utils.translator3 import BailianTranslator, save_translated_data
from utils.cv_inpaint import process_image_with_ocr_data
import config

app = FastAPI()

SAVE_DIR = "./received_images"
TAR_LANG = "Chinese" # 默认是中文
os.makedirs(SAVE_DIR, exist_ok=True)



# 全局变量用于跟踪PaddleX服务状态
paddlex_process = None
paddlex_started = False

api_key = config.DASHSCOPE_API_KEY

def start_paddlex_service():
    """启动PaddleX OCR服务"""
    global paddlex_process, paddlex_started
    
    try:
        # 检查是否已经启动
        if paddlex_started and paddlex_process and paddlex_process.poll() is None:
            print("[+] PaddleX服务已在运行")
            return True
            
        # 启动PaddleX服务
        print("[+] 正在启动PaddleX OCR服务...")
        
        # 使用conda环境执行命令
        cmd = [
            "conda", "run", "-n", "paddle-ocr",
            "paddlex", "--serve", "--pipeline", "./OCR.yaml", 
            "--host", "0.0.0.0",
            "--port", "8080"
        ]
        
        # 启动进程
        paddlex_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待一段时间让服务启动
        time.sleep(10)
        
        # 检查进程是否仍在运行
        if paddlex_process.poll() is None:
            paddlex_started = True
            print("[+] PaddleX OCR服务启动成功")
            return True
        else:
            # 读取错误输出
            stdout, stderr = paddlex_process.communicate()
            print(f"[!] PaddleX服务启动失败: {stderr}")
            return False
            
    except Exception as e:
        print(f"[!] 启动PaddleX服务时出错: {e}")
        return False

def install_paddlex_serving():
    """安装PaddleX服务组件"""
    try:
        print("[+] 正在安装PaddleX服务组件...")
        cmd = [
            "conda", "run", "-n", "paddle-ocr",
            "paddlex", "--install", "serving"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print("[+] PaddleX服务组件安装成功")
            return True
        else:
            print(f"[!] PaddleX服务组件安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"[!] 安装PaddleX服务组件时出错: {e}")
        return False

def initialize_paddlex_service():
    """初始化PaddleX服务（安装+启动）"""
    # 首先尝试安装服务组件
    if install_paddlex_serving():
        # 然后启动服务
        return start_paddlex_service()
    return False

def cleanup_paddlex_service():
    """清理PaddleX服务"""
    global paddlex_process
    if paddlex_process and paddlex_process.poll() is None:
        print("[+] 正在关闭PaddleX服务...")
        paddlex_process.terminate()
        try:
            paddlex_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            paddlex_process.kill()
        print("[+] PaddleX服务已关闭")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器"""
    # 应用启动时的初始化操作
    print("[+] 应用启动，正在初始化PaddleX OCR服务...")
    # 在后台线程中启动服务，避免阻塞应用启动
    thread = threading.Thread(target=initialize_paddlex_service)
    thread.daemon = True
    thread.start()
    
    yield  # 应用运行期间
    
    # 应用关闭时的清理操作
    cleanup_paddlex_service()
    print("[+] 应用已关闭")

# 使用lifespan参数创建FastAPI应用
app = FastAPI(lifespan=lifespan)

@app.post("/")
async def receive_images(request: Request):
    global TAR_LANG
    form = await request.form()

    files = []
    saved_files = []   # ← 这里要先定义！否则下面用的时候会 NameError
    saved_files_translated = []
    # 1. 从表单中提取所有文件
    for key, value in form.items():
        if hasattr(value, "filename"):  # s是文件字段
            files.append(value)
        if key == "target_lang": # 目标语言字段
            TAR_LANG = value


    print(f"[+] Received {len(files)} files, target language: {TAR_LANG}")

    # 2. 保存并处理所有文件
    for file in files:
        file_bytes = await file.read()
        save_path = os.path.join(SAVE_DIR, file.filename)

        with open(save_path, "wb") as f:
            f.write(file_bytes)

        saved_files.append(save_path)
        print(f"[+] Saved:", save_path)


        # 3. 对保存的图片进行OCR识别
        image_path = save_path
        # 文件名逻辑
        filename = os.path.basename(image_path)
        parent_dir = os.path.dirname(image_path)

        # OCR逻辑
        base64_image = image_to_base64(image_path)
        ocr_result = ocr_image(base64_image)
        extracted_texts = extract_text(ocr_result)
        print("提取的文字:", extracted_texts)
        # 存储
        with open(f"{parent_dir}/{filename}.json", "w") as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)
        print(f"识别结果存储在：{parent_dir}/{filename}.json")

        # api翻译
        # 初始化翻译器
        api_key = "已隐藏"
        translator = BailianTranslator(api_key)
        
        translated_data = translator.translate_json_file(f"{parent_dir}/{filename}.json", target_lang=TAR_LANG)
        save_translated_data(translated_data, f"{parent_dir}/{filename}_translated.json")
        print(f"翻译结果已保存到 {parent_dir}/{filename}_translated.json")

        
        # 4. 使用cv2进行inpaint
        image = process_image_with_ocr_data(image_path, f"{parent_dir}/{filename}_translated.json", f"./final_results/{filename}_translated.jpg")
        print(f"[+] 处理后的图片已保存为：./final_results/{filename}_translated.jpg")
        saved_files_translated.append(f"./final_results/{filename}_translated.jpg")

        # 5. 删除原图
        os.remove(image_path)
        os.remove(f"{parent_dir}/{filename}.json")
        os.remove(f"{parent_dir}/{filename}_translated.json")
        print(f"[+] 删除原图及其json：{image_path}")

    # 6. 打成 ZIP 返回前端
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in saved_files_translated:
            zipf.write(path, arcname=os.path.basename(path))

    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=results.zip"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
