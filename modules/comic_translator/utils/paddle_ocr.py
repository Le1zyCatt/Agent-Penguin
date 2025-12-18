import base64
import json
import requests
from pathlib import Path

# PaddleOCR 服务地址
OCR_URL = "http://localhost:8080/ocr"

def image_to_base64(file_path):
    """将图片文件转换为 Base64 编码"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def ocr_image(file_base64, visualize=False):
    """调用 PaddleOCR 服务进行识别"""
    payload = {
        "file": file_base64,
        "fileType": 1,  # 1表示图像
        "visualize": visualize
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(OCR_URL, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("errorCode", 1) == 0:
            return result["result"]  # 返回识别结果 JSON
        else:
            raise RuntimeError(f"OCR 服务错误: {result.get('errorMsg')}")
    else:
        raise RuntimeError(f"OCR 请求失败，HTTP 状态码: {response.status_code}")

def extract_text(ocr_result):
    """从 PaddleOCR 返回结果中提取文字"""
    texts = []
    for page in ocr_result.get("ocrResults", []):
        pruned = page.get("prunedResult", {})
        for item in pruned.get("res", []):
            text = item.get("text")
            if text:
                texts.append(text)
    return texts

def process_image_sequence(image_paths):
    """批量处理图片序列"""
    all_results = []
    for img_path in image_paths:
        if Path(img_path).exists():
            file_base64 = image_to_base64(img_path)
        else:
            file_base64 = img_path  # 已经是Base64
        ocr_result = ocr_image(file_base64)
        texts = extract_text(ocr_result)
        all_results.append({
            "image": img_path,
            "texts": texts,
            "raw_result": ocr_result
        })
    return all_results,ocr_result

if __name__ == "__main__":
    # 测试图片序列（可以是文件路径，也可以是 Base64）
    image_seq = ["./test_data/jap.jpg", "./test_data/chi.jpg"]
    results,ori_results = process_image_sequence(image_seq)
    # print(ori_results)
    print(json.dumps(ori_results, indent=2, ensure_ascii=False))