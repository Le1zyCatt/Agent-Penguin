import json
# =========================
# 1. 加载 JSON 数据
# =========================
with open("data/history_json/OmoT.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)
    print(f"✅ 已加载 JSON 数据，共 {len(json_data)} 条记录")

# =========================
# 2. LangChain 转换为 Document
# =========================
from langchain_core.documents import Document

documents = [
    Document(
        page_content=item["text"],
        metadata={
            "id": item["id"],
            "name": item["name"],
            "time": item["time"],
            "msgtype": item["msgtype"]
        }
    )
    for item in json_data
]

print(f"✅ 转换为 Document 完成，共 {len(documents)} 条记录")
print(documents[0].page_content, documents[0].metadata)
print("✅ 以上为前10条。")

# =========================
# 3. 文本 Chunking
# =========================
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # 每块最大字符数
    chunk_overlap=10,   # 重叠字符数
    separators=["\n\n", "\n", "。", "！", "？", " ", ""]
)

chunks = splitter.split_documents(documents)
print(f"✅ 文本切分完成，总共 {len(chunks)} 个 chunk")
for chunk in chunks[0:10]:
    print(chunk.page_content, chunk.metadata)
    print(chunk,"\n")
print("✅ 以上为前10个 chunk。")

# =========================
# 4. Embedding
# =========================
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="models/embedding/m3e-small")

# =========================
# 5. 转换成向量
# =========================
# FAISS 需要的就是直接把 Document 列表传入向量数据库，它会自动计算 embedding
# 但如果你想单独拿 vector，也可以：
vectors = [embedding_model.embed_documents([chunk.page_content])[0] for chunk in chunks]

# =========================
# 6. 存入向量数据库（FAISS）
# =========================
from langchain_community.vectorstores import FAISS

vector_db = FAISS.from_documents(chunks, embedding_model)

# 保存到本地
vector_db.save_local("data/chat_vector_db")
print("✅ 已保存向量数据库到 data/chat_vector_db")

# =========================
# 7. 测试 top-k 检索
# =========================
query = "可爱妹妹"
results = vector_db.similarity_search(query, k=20)
print(results,"\n")
print("🔎 top-k 检索结果：")
for r in results:
    print(f"内容：{r.page_content}")
    print(f"说话者：{r.metadata['name']}, 时间：{r.metadata['time']}")
    print("-" * 50)
