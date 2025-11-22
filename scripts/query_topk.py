from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# 加载本地模型、向量数据库
embedding_model = HuggingFaceEmbeddings(model_name="models/embedding/m3e-small")
vector_db = FAISS.load_local("data/chat_vector_db", embedding_model, allow_dangerous_deserialization=True)

# 执行相似性搜索
query = "斐济杯"  # 查询关键词
k = 20             # 返回最相似的20个结果

results = vector_db.similarity_search(query, k=k)

# 输出结果
print("🔎 Top-K 检索结果：")
for idx, r in enumerate(results):
    print(f"[{idx+1}] 内容：{r.page_content}")
    print(f"    说话者：{r.metadata['name']}, 时间：{r.metadata['time']}")
    print("-" * 50)