#!/usr/bin/env python3
"""
测试翻译功能的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.msg.translator import BailianTranslator
import config

def test_translation():
    print("开始测试翻译功能...")
    
    # 创建翻译器实例
    translator = BailianTranslator(config.DASHSCOPE_API_KEY)
    
    # 测试文本
    test_text = "Hello, this is a test translation."
    print(f"原始文本: {test_text}")
    
    try:
        # 调用翻译API
        result = translator._call_api(test_text, mode="translate", target_lang="Chinese")
        print(f"翻译结果: {result}")
        
        # 检查是否与原文相同（如果API调用失败，通常会返回原文）
        if result == test_text:
            print("警告: 翻译结果与原文相同，可能API调用有问题")
        else:
            print("翻译成功!")
            
    except Exception as e:
        print(f"翻译过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_translation()
