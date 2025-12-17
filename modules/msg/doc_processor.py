# modules/doc_processor.py
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from translator import BailianTranslator
import config

def process_document_summary(file_path: str, task_type: str = "summarize", target_lang: str = "Chinese"):
    """
    读取文档 -> 提取文本 -> 调用大模型总结/翻译
    """
    # 1. 识别并加载文档
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext in [".docx", ".doc"]:
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            return f"暂不支持 {ext} 格式"
            
        docs = loader.load()
        # 简单合并所有页面的文本
        full_text = "\n".join([d.page_content for d in docs])
        
        # 2. 长度截断 (防止 Token 爆炸，生产环境建议用 Map-Reduce 分段处理)
        # 简单截取前 15000 字符
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n...(内容过长已截断)..."

        # 3. 调用 AI
        translator = BailianTranslator(config.DASHSCOPE_API_KEY)
        result = translator._call_api(full_text, mode=task_type, target_lang=target_lang)
        
        return result

    except Exception as e:
        return f"处理文档失败: {str(e)}"