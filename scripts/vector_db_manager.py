# vector_db_manager.py
# 供topk_api_module.py调：加载指定向量数据库，根据关键词返回特定对象的聊天记录topk
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import json
import os

class VectorDBManager:
    def __init__(self, db_path="data/chat_vector_db", model_name="models/embedding/m3e-small"):
        """
        初始化向量数据库管理器
        
        Args:
            db_path (str): 向量数据库路径
            model_name (str): 嵌入模型名称
        """
        self.db_path = db_path
        self.model_name = model_name
        self.embedding_model = None
        self.vector_db = None
        self._load_vector_database()
    
    def _load_vector_database(self):
        """加载向量数据库"""
        try:
            self.embedding_model = HuggingFaceEmbeddings(model_name=self.model_name)
            self.vector_db = FAISS.load_local(
                self.db_path, 
                self.embedding_model, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            raise RuntimeError(f"无法加载向量数据库: {e}")
    
    def search_by_contact(self, contact_name, query, k=20):
        """
        根据联系人姓名和查询内容检索相关信息
        
        Args:
            contact_name (str): 聊天对象姓名
            query (str): 查询关键词
            k (int): 返回最相似的k个结果
            
        Returns:
            list: 检索结果列表
        """
        # 可以根据contact_name做一些特殊处理，比如过滤特定联系人的消息
        # 当前版本暂时不实现过滤，后续可以扩展
        
        try:
            results = self.vector_db.similarity_search(query, k=k)
            return results
        except Exception as e:
            raise RuntimeError(f"检索过程中发生错误: {e}")
    
    def get_contact_list(self, json_dir="data/history_json"):
        """
        获取所有联系人列表
        
        Args:
            json_dir (str): JSON文件目录
            
        Returns:
            list: 联系人姓名列表
        """
        contacts = []
        try:
            if os.path.exists(json_dir):
                for filename in os.listdir(json_dir):
                    if filename.endswith('.json'):
                        contact_name = filename.replace('.json', '')
                        contacts.append(contact_name)
            return contacts
        except Exception as e:
            raise RuntimeError(f"获取联系人列表失败: {e}")

