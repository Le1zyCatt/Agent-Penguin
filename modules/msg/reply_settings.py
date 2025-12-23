"""
自动回复设置管理模块
用于管理每个聊天会话的自动回复启用状态
"""
import json
import os
import config


# 自动回复设置存储文件路径
REPLY_SETTINGS_FILE = os.path.join(config.DATA_DIR, "reply_settings.json")


def load_reply_settings():
    """
    加载自动回复设置
    返回: dict, 格式为 {contact_id: {"enabled": bool, "updated_at": str}}
    """
    if not os.path.exists(REPLY_SETTINGS_FILE):
        # 如果文件不存在，创建默认设置
        default_settings = {}
        save_reply_settings(default_settings)
        return default_settings
    
    try:
        with open(REPLY_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ReplySettings] 加载设置失败: {e}")
        return {}


def save_reply_settings(settings):
    """
    保存自动回复设置
    参数: settings, dict, 格式为 {contact_id: {"enabled": bool, "updated_at": str}}
    """
    try:
        # 确保目录存在
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        with open(REPLY_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ReplySettings] 保存设置失败: {e}")
        return False


def get_reply_setting(contact_id):
    """
    获取特定聊天会话的自动回复设置
    参数: contact_id, str, 聊天会话ID
    返回: bool, 是否启用自动回复
    """
    settings = load_reply_settings()
    contact_setting = settings.get(contact_id, {})
    # 如果没有特定设置，则使用全局设置
    if "enabled" in contact_setting:
        return contact_setting["enabled"]
    else:
        return config.AUTO_REPLY_ENABLED


def set_reply_setting(contact_id, enabled):
    """
    设置特定聊天会话的自动回复状态
    参数: 
        contact_id, str, 聊天会话ID
        enabled, bool, 是否启用自动回复
    返回: bool, 是否设置成功
    """
    from datetime import datetime
    
    settings = load_reply_settings()
    
    # 更新指定聊天会话的设置
    settings[contact_id] = {
        "enabled": enabled,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return save_reply_settings(settings)


def get_all_reply_settings():
    """
    获取所有聊天会话的自动回复设置
    返回: dict, 所有聊天会话的设置
    """
    return load_reply_settings()
