# modules/comic_translator/core.py
import os
import json
import zipfile
import io
import requests

# 导入同级模块
from .paddle_ocr import image_to_base64
# 注意：你需要修改 paddle_ocr.py 让它支持从 config 读取 URL，或者在这里手动传 URL
from .translator3 import BailianTranslator
from .cv_inpaint import process_image_with_ocr_data

# 导入全局配置
import config

def ocr_image_request(file_base64, server_url):
    """
    本地封装的 OCR 请求函数，使用 config 中的 URL
    替代 paddle_ocr.py 中硬编码的 URL
    """
    payload = {
        "file": file_base64,
        "fileType": 1, 
        "visualize": False
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(server_url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get("errorCode", 1) == 0:
                return result["result"]
            else:
                raise RuntimeError(f"OCR 服务错误: {result.get('errorMsg')}")
        else:
            raise RuntimeError(f"OCR HTTP 错误: {response.status_code}")
    except Exception as e:
        raise RuntimeError(f"连接 OCR 服务失败 ({server_url}): {e}")

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def process_comic_images(image_paths: list, target_lang: str):
    """
    核心业务流程：批量处理图片
    """
    saved_files_translated = []
    
    # 初始化翻译器
    translator = BailianTranslator(config.DASHSCOPE_API_KEY)

    try:
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            # parent_dir 应该是临时文件夹路径
            parent_dir = os.path.dirname(image_path)
            
            print(f"[Core] 正在处理: {filename}")

            # ---------------------------
            # 1. OCR 识别
            # ---------------------------
            base64_img = image_to_base64(image_path)
            # 使用 config.OCR_URL
            ocr_result = ocr_image_request(base64_img, config.OCR_URL)
            
            # 保存 OCR 原始结果 (xxx.json)
            json_filename = f"{filename}.json"
            json_path = os.path.join(parent_dir, json_filename)
            save_json(ocr_result, json_path)

            # ---------------------------
            # 2. 文本翻译
            # ---------------------------
            trans_json_filename = f"{filename}_translated.json"
            trans_json_path = os.path.join(parent_dir, trans_json_filename)
            
            # 调用 translator.py 中的逻辑
            translated_data = translator.translate_json_file(json_path, target_lang=target_lang)
            save_json(translated_data, trans_json_path)

            # ---------------------------
            # 3. 图像回填 (Inpaint + 嵌字)
            # ---------------------------
            output_filename = f"trans_{filename}"
            output_path = os.path.join(parent_dir, output_filename)
            
            # 调用 cv_inpaint.py (需确保该文件已不再硬编码字体路径)
            process_image_with_ocr_data(
                image_path=image_path,
                json_path=trans_json_path,
                output_path=output_path,
                font_path=config.FONT_PATH  # 从 config 传入字体路径
            )
            
            saved_files_translated.append(output_path)
            print(f"[Core] 完成: {output_filename}")

            # (可选) 清理中间 JSON 文件，保持文件夹整洁
            # if os.path.exists(json_path): os.remove(json_path)
            # if os.path.exists(trans_json_path): os.remove(trans_json_path)

        # ---------------------------
        # 4. 打包为 ZIP
        # ---------------------------
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in saved_files_translated:
                # arcname 确保 zip 包里没有层层叠叠的目录，只有文件名
                zipf.write(path, arcname=os.path.basename(path))
        
        zip_buf.seek(0)
        return zip_buf

    except Exception as e:
        print(f"[Core] 处理过程出错: {e}")
        # 如果出错了，最好把已经生成的文件也清理一下，或者抛出异常给 API 层处理
        raise e