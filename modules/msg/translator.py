# modules/comic_translator/translator.py
import json
import requests
import time
from typing import List, Dict, Any, Union
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class BailianTranslator:
    """
    百炼翻译器 - 保持原格式的翻译模块
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
    
    def _call_api(self, text: str, mode: str = "translate", target_lang: str = "Chinese") -> str:
        """
        核心调用方法：支持翻译和总结
        """
        if not text or not text.strip():
            return ""

        # 根据模式构建 Prompt
        if mode == "translate":
            prompt = f"Translate the following text to {target_lang}. Only output the translated text without explanations:\n\n{text}"
        elif mode == "summarize":
            prompt = f"请阅读以下文本，并用{target_lang}生成一份精炼的摘要总结，提取核心信息：\n\n{text}"
        else:
            prompt = text 

        payload = {
            "model": "qwen-plus",
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"max_tokens": 2000, "temperature": 0.3}
        }
        
        try:
            response = self.session.post(self.api_url, headers=self.headers, json=payload, timeout=300)
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'text' in result['output']:
                    # 尝试清洗可能存在的 markdown 标记
                    clean_text = result['output']['text'].strip()
                    return clean_text.replace("```json", "").replace("```", "")
                elif 'output' in result and 'choices' in result['output']:
                     return result['output']['choices'][0]['message']['content'].strip()
            print(f"API Error: {response.text}")
            return text
        except Exception as e:
            print(f"Exception: {e}")
            return text

    def translate_json_file(self, file_path: Union[str, Path], target_lang: str = "Chinese") -> Union[List[Dict], Dict]:
        """
        翻译JSON文件 - 修复后的逻辑
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        translated_data = original_data.copy()

        # 检查是否是标准的 PaddleOCR 输出结构 (通常是字典，包含 'ocrResults')
        if isinstance(translated_data, dict) and "ocrResults" in translated_data:
            print("[Translator] 检测到标准 OCR 结果，开始翻译...")
            for i, page in enumerate(translated_data["ocrResults"]):
                pruned = page.get("prunedResult", {})
                rec_texts = pruned.get("rec_texts", [])
                
                if rec_texts:
                    # 将列表转为字符串发送给 LLM
                    # 修正点：这里强制 mode="translate"
                    text_to_translate = str(rec_texts)
                    translated_str = self._call_api(text_to_translate, mode="translate", target_lang=target_lang)
                    
                    # 尝试把翻译回来的字符串变回列表 (为了保持JSON格式兼容性)
                    try:
                        import ast
                        # 只有当 LLM 严格返回列表格式字符串时才转换
                        if translated_str.startswith("[") and translated_str.endswith("]"):
                            translated_list = ast.literal_eval(translated_str)
                            translated_data['ocrResults'][i]['prunedResult']['rec_texts'] = translated_list
                        else:
                            # 否则存为字符串，cv_inpaint.py 里有逻辑处理这种情况
                            translated_data['ocrResults'][i]['prunedResult']['rec_texts'] = translated_str
                    except:
                        translated_data['ocrResults'][i]['prunedResult']['rec_texts'] = translated_str
        else:
            print("[Translator] JSON 结构无法识别，跳过翻译")

        return translated_data