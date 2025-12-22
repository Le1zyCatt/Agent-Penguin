#!/usr/bin/env python3
import requests
import json

def test_summarize():
    print("=== 消息总结功能测试 ===")
    
    # 1. 获取联系人列表
    print("\n1. 获取联系人列表...")
    try:
        response = requests.get("http://localhost:8000/api/msg/list")
        data = response.json()
        
        if data.get("status") == "success":
            contacts = data.get("data", [])
            if not contacts:
                print("❌ 没有找到聊天记录")
                return False
            
            print(f"✅ 找到 {len(contacts)} 个聊天对象")
            for i, contact in enumerate(contacts):
                print(f"   {i+1}. ID: {contact['id']} | 类型: {contact['type']}")
            
            # 选择第一个联系人进行测试
            contact_id = contacts[0]["id"]
            print(f"\n2. 使用联系人 {contact_id} 进行消息总结测试")
            
            # 3. 调用总结API
            print("3. 调用消息总结API...")
            api_url = "http://localhost:8000/api/msg/summarize"
            payload = {
                "contact_id": contact_id,
                "limit": 50,
                "target_lang": "Chinese"
            }
            
            response = requests.post(api_url, data=payload)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if result.get("success"):
                    print("✅ 消息总结成功!")
                    return True
                else:
                    print("❌ 消息总结失败")
                    return False
            else:
                print(f"❌ API请求失败: {response.text}")
                return False
        else:
            print("❌ 获取联系人列表失败")
            return False
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        print("💡 提示: 请确保服务器已启动 (python server.py)")
        return False

if __name__ == "__main__":
    test_summarize()

