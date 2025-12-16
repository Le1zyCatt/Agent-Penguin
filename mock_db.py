# mock_db.py 用于创建伪造的空数据集
import os
import shutil
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import config

def create_mock_db():
    print("🚧 正在创建伪造的空数据库，仅用于测试启动...")

    # 1. 准备一条假数据
    dummy_docs = [
        Document(
            page_content="这是一个测试数据库，用于在没有真实数据时启动服务器。",
            metadata={"source": "mock", "name": "System", "time": "2025-01-01"}
        )
    ]

    # 2. 加载模型 (如果没有下载模型，这步会自动下载 m3e-small，约 80MB)
    print("📥 加载/下载 Embedding 模型 (m3e-small)...")
    # 注意：如果网络不通，这步可能会卡住。如果卡住，请确保你能访问 HuggingFace 
    # 或者将 model_name 改为 "shibing624/text2vec-base-chinese" 试试
    embedding_model = HuggingFaceEmbeddings(model_name="models/embedding/m3e-small")

    # 3. 生成向量库
    print("⚙️ 生成向量索引...")
    vector_db = FAISS.from_documents(dummy_docs, embedding_model)

    # 4. 保存到 config 指定的目录
    save_path = config.VECTOR_DB_PATH
    
    # 如果目录已存在，先清空，防止冲突
    if os.path.exists(save_path):
        shutil.rmtree(save_path)
    os.makedirs(save_path, exist_ok=True)

    vector_db.save_local(save_path)
    
    print(f"✅ 伪造数据库已保存到: {save_path}")
    print("🎉 现在你可以运行 python server.py 了，不会再报错了！")

if __name__ == "__main__":
    create_mock_db()