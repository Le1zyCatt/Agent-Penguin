# modules/doc_processor.py
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from .translator import BailianTranslator
import config

# 新增：只提取文本，不总结
def extract_text_from_file(file_path: str, max_chars: int = 1000) -> str:
    """
    读取文件内容并返回字符串
    max_chars: 限制读取长度，防止Token爆炸
    """
    if not os.path.exists(file_path):
        return "[文件不存在]"

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext in [".docx", ".doc"]:
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            return f"[不支持的文件格式: {ext}]"
            
        docs = loader.load()
        full_text = "\n".join([d.page_content for d in docs])
        
        # 简单清洗空格
        full_text = full_text.strip()
        
        if len(full_text) > max_chars:
            return full_text[:max_chars] + "...(剩余内容已截断)"
        return full_text if full_text else "[空文件]"

    except Exception as e:
        return f"[读取文件出错: {str(e)}]"

# 原有函数保持不变，但可以调用上面的函数来简化逻辑
def process_document_summary(file_path: str, task_type: str = "summarize", target_lang: str = "Chinese"):
    # 复用上面的提取逻辑
    full_text = extract_text_from_file(file_path, max_chars=15000)
    
    if full_text.startswith("["): # 简单的错误检查
        if "出错" in full_text or "不支持" in full_text:
            return full_text

    translator = BailianTranslator(config.DASHSCOPE_API_KEY)
    result = translator._call_api(full_text, mode=task_type, target_lang=target_lang)
    return result