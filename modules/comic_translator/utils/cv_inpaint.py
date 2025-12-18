# draw_ocr_boxes.py
import cv2
import numpy as np
from typing import List, Union
import os
import json
from PIL import Image, ImageDraw, ImageFont

def draw_ocr_boxes_on_image(
    image: Union[np.ndarray, str],
    boxes: List[List[List[int]]],
    color: tuple = (255, 0, 0),
    thickness: int = 2,
) -> np.ndarray:
    """
    在图像上绘制 OCR 检测框（四点格式），不显示识别文本。

    Args:
        image (np.ndarray or str): 输入图像（BGR 格式的 numpy array）或图像路径。
        boxes (List[List[List[int]]]): 检测框列表，每个框为 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        color (tuple): 框颜色，格式为 (B, G, R)，默认为红色 (255, 0, 0)
        thickness (int): 线条粗细，默认为 2

    Returns:
        np.ndarray: 绘制了检测框的图像（BGR 格式，可用于 cv2.imwrite 或 cv2.imshow）
    """
    # 读取图像（如果传入的是路径）
    if isinstance(image, str):
        if not os.path.exists(image):
            raise FileNotFoundError(f"图像路径不存在: {image}")
        img = cv2.imread(image)
        if img is None:
            raise ValueError(f"无法读取图像: {image}")
    elif isinstance(image, np.ndarray):
        img = image.copy()
    else:
        raise TypeError("参数 `image` 必须是图像路径(str)或 BGR 格式的 numpy array")

    # 绘制每个框
    for box in boxes:
        pts = np.array(box, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)

    return img

def extract_ocr_data_from_json(json_path: str) -> dict:
    """
    从JSON文件中提取OCR数据，包括检测框和识别文本
    
    Args:
        json_path (str): JSON文件路径
        
    Returns:
        dict: 包含boxes和texts的字典
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 提取OCR结果
    ocr_results = data.get("ocrResults", [])
    if not ocr_results:
        raise ValueError("JSON文件中未找到ocrResults字段")
    
    # 获取第一个结果中的prunedResult
    pruned_result = ocr_results[0].get("prunedResult", {})
    
    # 提取检测框坐标
    boxes = pruned_result.get("dt_polys", [])
    
    # 提取识别文本
    # 注意：rec_texts可能是一个字符串表示的列表，需要解析
    rec_texts_raw = pruned_result.get("rec_texts", [])
    if isinstance(rec_texts_raw, str):
        # 如果是字符串形式的列表，需要解析
        try:
            import ast
            rec_texts = ast.literal_eval(rec_texts_raw)
        except:
            # 如果解析失败，尝试手动解析
            # 移除首尾的方括号和引号，按逗号分割
            cleaned = rec_texts_raw.strip("[]")
            # 分割但保留引号内的逗号
            rec_texts = []
            current = ""
            in_quote = False
            i = 0
            while i < len(cleaned):
                if cleaned[i] == "'" and (i == 0 or cleaned[i-1] != "\\"):
                    in_quote = not in_quote
                elif cleaned[i] == "," and not in_quote:
                    rec_texts.append(current.strip().strip("'"))
                    current = ""
                    # 跳过空格
                    while i+1 < len(cleaned) and cleaned[i+1] == " ":
                        i += 1
                else:
                    current += cleaned[i]
                i += 1
            if current.strip():
                rec_texts.append(current.strip().strip("'"))
    else:
        rec_texts = rec_texts_raw
    
    return {
        "boxes": boxes,
        "texts": rec_texts
    }

def erase_text_areas(image: np.ndarray, boxes: List[List[List[int]]]) -> np.ndarray:
    """
    使用OpenCV的inpaint算法擦除图像中的文本区域
    
    Args:
        image (np.ndarray): 输入图像
        boxes (List[List[List[int]]]): 文本区域的检测框列表
        
    Returns:
        np.ndarray: 擦除了文本区域的图像
    """
    # 创建掩码
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    # 在掩码上绘制所有文本区域
    for box in boxes:
        pts = np.array(box, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    
    # 使用inpaint算法填充文本区域
    result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
    
    return result

def embed_texts_in_image(image: np.ndarray, boxes: List[List[List[int]]], 
                        texts: List[str], font_path: str = None) -> np.ndarray:
    # BGR → RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    draw = ImageDraw.Draw(pil_image)

    # 加载字体
    def load_font(size):
        try:
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            else:
                return ImageFont.load_default()
        except:
            return ImageFont.load_default()

    # 判断英文 → 固定横排
    def is_english(s):
        for ch in s:
            if 'a' <= ch.lower() <= 'z':
                return True
        return False

    # ---------- 计算全局统一字体大小 ----------
    max_font_size = 200  # 假设最大尝试200
    global_font_size = max_font_size

    for box, text in zip(boxes, texts):
        if not text:
            continue
        pts = np.array(box, dtype=np.int32)
        x_min, y_min = np.min(pts[:,0]), np.min(pts[:,1])
        x_max, y_max = np.max(pts[:,0]), np.max(pts[:,1])
        box_w, box_h = x_max - x_min, y_max - y_min

        mode = "horizontal" if is_english(text) else ("vertical" if box_h > box_w else "horizontal")

        # 从大到小尝试字体大小
        for size in range(max_font_size, 0, -1):
            font = load_font(size)
            if mode == "horizontal":
                # 横排：用换行保证宽度不超框
                lines = wrap_text(text, font, box_w)
                total_h = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines])
                if total_h <= box_h:
                    global_font_size = min(global_font_size, size) + 1 # 稍微调大一点字体
                    break
            else:
                # 竖排
                total_h = sum([font.getbbox(ch)[3] - font.getbbox(ch)[1] for ch in text])
                max_w = max([font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text])
                if total_h <= box_h and max_w <= box_w:
                    global_font_size = min(global_font_size, size) + 1 # 稍微调大一点字体
                    break

    font = load_font(global_font_size)

    # ---------- 绘制文本 ----------
    for box, text in zip(boxes, texts):
        if not text:
            continue
        pts = np.array(box, dtype=np.int32)
        x_min, y_min = np.min(pts[:,0]), np.min(pts[:,1])
        x_max, y_max = np.max(pts[:,0]), np.max(pts[:,1])
        box_w, box_h = x_max - x_min, y_max - y_min

        mode = "horizontal" if is_english(text) else ("vertical" if box_h > box_w else "horizontal")

        if mode == "horizontal":
            lines = wrap_text(text, font, box_w)
            total_h = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines])
            current_y = y_min + (box_h - total_h) // 2
            for line in lines:
                line_w = font.getbbox(line)[2] - font.getbbox(line)[0]
                draw.text((x_min + (box_w - line_w)//2, current_y), line, fill=(0,0,0), font=font)
                current_y += font.getbbox(line)[3] - font.getbbox(line)[1]
        else:
            # 竖排
            total_h = sum([font.getbbox(ch)[3] - font.getbbox(ch)[1] for ch in text])
            current_y = y_min + (box_h - total_h)//2
            for ch in text:
                ch_w = font.getbbox(ch)[2] - font.getbbox(ch)[0]
                draw.text((x_min + (box_w - ch_w)//2, current_y), ch, fill=(0,0,0), font=font)
                current_y += font.getbbox(ch)[3] - font.getbbox(ch)[1]

    result = np.array(pil_image)
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)




def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    简单的文本换行函数
    
    Args:
        text (str): 要换行的文本
        font (ImageFont): 字体对象
        max_width (int): 最大宽度
        
    Returns:
        List[str]: 换行后的文本列表
    """
    if not text:
        return []
    
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = (current_line + " " + word).strip()
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
        
    return lines if lines else [text]

def process_image_with_ocr_data(image_path: str, json_path: str, output_path: str,
                               font_path: str = "/home/le1zycatt/Desktop/vscode_py/manga/fonts/simhei.ttf"):
    """
    处理图像：绘制框、擦除文本、嵌入新文本
    
    Args:
        image_path (str): 图像路径
        json_path (str): JSON数据路径
        output_path (str): 输出路径
        font_path (str): 字体路径
    """
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    # 提取OCR数据
    ocr_data = extract_ocr_data_from_json(json_path)
    boxes = ocr_data["boxes"]
    texts = ocr_data["texts"]
    
    # 步骤1: 绘制OCR检测框（可选，用于调试）
    boxed_image = draw_ocr_boxes_on_image(image, boxes, color=(0, 255, 0), thickness=2)
    # cv2.imwrite(output_path.replace(".jpg", "_boxed.jpg"), boxed_image)
    
    # 步骤2: 擦除文本区域
    erased_image = erase_text_areas(image, boxes)
    # cv2.imwrite(output_path.replace(".jpg", "_erased.jpg"), erased_image)
    
    # 步骤3: 嵌入新文本
    final_image = embed_texts_in_image(erased_image, boxes, texts, font_path)
    cv2.imwrite(output_path, final_image)
    
    return final_image

# ========================
# 示例用法
# ========================
if __name__ == "__main__":
    # # 示例1：绘制OCR检测框
    # print("示例1：绘制OCR检测框")
    # img = cv2.imread("/home/le1zycatt/Desktop/vscode_py/manga/received_images/11.webp")
    # ocr_data = extract_ocr_data_from_json("/home/le1zycatt/Desktop/vscode_py/manga/received_images/11.webp_translated.json")
    # boxes = ocr_data["boxes"]
    
    # out = draw_ocr_boxes_on_image(img, boxes, color=(0, 255, 0), thickness=2)
    # cv2.imwrite("./demo_boxes.jpg", out)
    # print("已保存带检测框的图像到 demo_boxes.jpg")
    
    # # 示例2：擦除文本区域
    # print("\n示例2：擦除文本区域")
    # erased_img = erase_text_areas(img, boxes)
    # cv2.imwrite("./demo_erased.jpg", erased_img)
    # print("已保存擦除文本后的图像到 demo_erased.jpg")
    
    # # 示例3：嵌入文本
    # print("\n示例3：嵌入文本")
    # texts = ocr_data["texts"]
    # embedded_img = embed_texts_in_image(erased_img, boxes, texts, 
    #                                    "/home/le1zycatt/Desktop/vscode_py/manga/fonts/simhei.ttf")
    # cv2.imwrite("./demo_embedded.jpg", embedded_img)
    # print("已保存嵌入文本后的图像到 demo_embedded.jpg")
    
    # 示例4：完整处理流程
    print("\n完整处理:")
    try:
        final_img = process_image_with_ocr_data(
            "/home/le1zycatt/Desktop/vscode_py/manga/received_images/11.webp",
            "/home/le1zycatt/Desktop/vscode_py/manga/received_images/11.webp_translated.json",
            "./demo_final.jpg"
        )
        print("已完成完整处理流程，结果保存到 demo_final.jpg")
    except Exception as e:
        print(f"处理过程中出错: {e}")

    # # 示例5：仅显示提取的数据
    # print("\n示例5：提取的OCR数据信息")
    # print(f"提取到 {len(boxes)} 个文本框")
    # print(f"前5个识别文本:")
    # for i, text in enumerate(texts[:5]):
    #     print(f"  {i+1}. {text}")