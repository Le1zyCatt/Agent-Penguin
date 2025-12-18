# topk_api_module.py
from .vector_db_manager import VectorDBManager

def search_messages_api(contact_name, query, k=20, n=1):
    """
    API接口：根据联系人姓名和查询内容检索消息，并返回每条消息的下n条消息
    
    Args:
        contact_name (str): 聊天对象姓名
        query (str): 查询关键词
        k (int): 返回相似结果数量
        n (int): 每条相似消息返回的后续消息数量
        
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
            # 获取当前消息的ID
            message_id = result.metadata.get('id', '')
            
            # 获取后续n条消息
            next_messages = []
            if message_id:
                try:
                    next_messages = db_manager.get_next_messages(contact_name, message_id, n)
                except Exception as e:
                    print(f"获取后续消息失败: {e}")
            
            # 格式化后续消息
            formatted_next_messages = []
            for msg in next_messages:
                formatted_next_messages.append({
                    "content": msg.get('text', ''),
                    "metadata": {
                        "name": msg.get('name', ''),
                        "time": msg.get('time', ''),
                        "id": msg.get('id', ''),
                        "msgtype": msg.get('msgtype', '')
                    }
                })
            
            formatted_results.append({
                "rank": idx + 1,
                "content": result.page_content,
                "metadata": {
                    "name": result.metadata.get('name', ''),
                    "time": result.metadata.get('time', ''),
                    "id": message_id,
                    "msgtype": result.metadata.get('msgtype', '')
                },
                "next_messages": formatted_next_messages,
                "next_count": len(formatted_next_messages)
            })
        
        return {
            "success": True,
            "contact": contact_name,
            "query": query,
            "total_results": len(formatted_results),
            "next_messages_count": n,
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
    # 示例：检索与"OmoT"的聊天中关于"可爱妹妹"的内容，并返回每条结果的下5条消息
    result = search_messages_api("OmoT", "可爱妹妹", 10, 5)
    
    if result["success"]:
        print(f"🔎 检索联系人: {result['contact']}")
        print(f"检索关键词: {result['query']}")
        print(f"找到 {result['total_results']} 条相关记录，每条返回下{result['next_messages_count']}条消息:")
        print("-" * 50)
        
        for item in result["results"]:
            print(f"[{item['rank']}] 内容: {item['content']}")
            print(f"    发送者: {item['metadata']['name']}, 时间: {item['metadata']['time']}")
            
            if item['next_count'] > 0:
                print(f"    后续消息 ({item['next_count']}条):")
                for next_msg in item['next_messages']:
                    print(f"        ▶️ {next_msg['metadata']['name']} ({next_msg['metadata']['time']}): {next_msg['content']}")
            
            print("-" * 30)
    else:
        print(f"❌ 检索失败: {result['error']}")