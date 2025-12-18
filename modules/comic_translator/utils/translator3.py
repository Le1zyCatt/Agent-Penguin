# translator.py
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
        """
        初始化翻译器
        
        Args:
            api_key: 百炼API密钥
        """
        self.api_key = api_key
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # 创建会话并配置重试机制
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
    
    def _call_api(self, text: str, context: str = "", target_lang: str = "Chinese") -> str:
        """
        调用百炼API进行翻译
        
        Args:
            text: 待翻译文本
            context: 上下文文本，用于提供整体理解
            target_lang: 目标语言代码
            
        Returns:
            翻译后的文本
        """
        
        target_lang_name = target_lang
        
        # 修改提示词，包含上下文

        prompt = f"Translate the following text to {target_lang_name}. Only output the translated text without any additional explanation:\n\n{text}.Return in the same format as the original text."
        
        payload = {
            "model": "qwen-plus",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": 2000,
                "temperature": 0.3  # 较低温度保证翻译准确性
            }
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 修正：检查API返回的实际结构
                    if 'output' in result:
                        # 尝试获取text字段（实际返回格式）
                        if 'text' in result['output']:
                            return result['output']['text'].strip()
                        # 保留原有逻辑以兼容可能的其他格式
                        elif 'choices' in result['output'] and result['output']['choices']:
                            return result['output']['choices'][0]['message']['content'].strip()
                    
                # 错误处理
                raise Exception(f"API call failed: {response.status_code} - {response.text}")
                
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                # 处理SSL和连接错误，进行重试
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Translation error for text '{text[:50]}...' after {max_retries} retries: {e}")
                    return text  # 翻译失败时返回原文
                print(f"SSL/Connection error, retrying ({retry_count}/{max_retries})...")
                time.sleep(1)  # 等待1秒后重试
            except Exception as e:
                print(f"Translation error for text '{text[:50]}...': {e}")
                return text  # 翻译失败时返回原文
    

    
    
    def translate_item(self, item: Dict[str, Any], target_lang: str = "en") -> Dict[str, Any]:
        """
        翻译单个项目
        
        Args:
            item: 包含id和rec_texts的字典
            target_lang: 目标语言代码
            
        Returns:
            翻译后的项目（保持相同格式）
        """
        translated_item = item.copy()
        # print(json.dumps(translated_item, ensure_ascii=False, indent=2))
        # 假设 item 是整个 ori_results.json 的内容
        if "ocrResults" in item:
            for ocr_result in item["ocrResults"]:  # 遍历每个OCR结果
                if "prunedResult" in ocr_result:
                    pruned_result = ocr_result["prunedResult"]
                    if "rec_texts" in pruned_result:
                        rec_texts = pruned_result["rec_texts"]
                        # 现在可以处理 rec_texts 了
                        # print("翻译前:",rec_texts)
                        translated_item['ocrResults'][0]['prunedResult']['rec_texts'] = self._call_api(rec_texts, "", target_lang)
        return translated_item
    

    def translate_json_file(self, file_path: Union[str, Path], target_lang: str = "Chinese") -> Union[List[Dict], Dict]:
        """
        翻译JSON文件
        
        Args:
            file_path: JSON文件路径
            target_lang: 目标语言代码
            
        Returns:
            翻译后的数据（保持原始结构）
        """
        # 读取原始文件
        with open(file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        # 翻译内容
        if isinstance(original_data, list):
            # 如果是数组，使用带上下文的翻译方法
            translated_data = self.translate_items_with_context(original_data, target_lang)
            print("list翻译")
        else:
            # 如果是单个对象，翻译该对象
            translated_data = self.translate_item(original_data, target_lang)
            print("单个翻译")
        return translated_data
    



def save_translated_data(data: Union[List[Dict], Dict], output_path: Union[str, Path]):
    """
    保存翻译后的数据
    
    Args:
        data: 翻译后的数据
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)