# topk_api_module.py
from .vector_db_manager import VectorDBManager

def search_messages_api(contact_name, query, k=20):
    """
    API接口：根据联系人姓名和查询内容检索消息
    
    Args:
        contact_name (str): 聊天对象姓名
        query (str): 查询关键词
        k (int): 返回结果数量
        
    Returns:
        dict: 包含检索结果的字典
    """
    try:
        # 初始化向量数据库管理器
        db_manager = VectorDBManager()
        
        # 执行检索
        results = db_manager.search_by_contact(contact_name, query, k)
        
        # 格式化结果
        formatted_results = []
        for idx, result in enumerate(results):
            formatted_results.append({
                "rank": idx + 1,
                "content": result.page_content,
                "metadata": {
                    "name": result.metadata.get('name', ''),
                    "time": result.metadata.get('time', ''),
                    "id": result.metadata.get('id', ''),
                    "msgtype": result.metadata.get('msgtype', '')
                }
            })
        
        return {
            "success": True,
            "contact": contact_name,
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "contact": contact_name,
            "query": query
        }

# 使用示例
if __name__ == "__main__":
    # 示例：检索与"OmoT"的聊天中关于"可爱妹妹"的内容
    result = search_messages_api("OmoT", "可爱妹妹", 10)
    
    if result["success"]:
        print(f"🔎 检索联系人: {result['contact']}")
        print(f"检索关键词: {result['query']}")
        print(f"找到 {result['total_results']} 条相关记录:")
        print("-" * 50)
        
        for item in result["results"]:
            print(f"[{item['rank']}] 内容: {item['content']}")
            print(f"    发送者: {item['metadata']['name']}, 时间: {item['metadata']['time']}")
            print("-" * 30)
    else:
        print(f"❌ 检索失败: {result['error']}") 