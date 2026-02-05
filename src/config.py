"""
配置管理模块
从 .env 文件或环境变量加载配置
"""
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "config" / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # 尝试加载根目录的 .env
    load_dotenv(PROJECT_ROOT / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    """获取布尔类型的环境变量"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def _get_int(key: str, default: int) -> int:
    """获取整数类型的环境变量"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


class Config:
    """应用配置类"""
    
    # 监控目标 URL
    TARGET_URL: str = os.getenv(
        "TARGET_URL",
        "https://m.stock.pingan.com/invest/zuhe/tradeRecord.html?productNo=5149"
    )
    
    # 检查间隔（秒）
    CHECK_INTERVAL: int = _get_int("CHECK_INTERVAL", 300)
    
    # 是否使用无头模式
    HEADLESS: bool = _get_bool("HEADLESS", True)
    
    # 用户代理（模拟 iPhone）
    USER_AGENT: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/15.0 Mobile/15E148 Safari/604.1"
    )
    
    # 页面加载超时（毫秒）
    PAGE_TIMEOUT: int = 30000
    
    # JS 渲染额外等待时间（毫秒）
    RENDER_WAIT: int = 3000
    
    COOKIES: str = os.getenv("COOKIES", "")
    COOKIES_FILE: str = os.getenv("COOKIES_FILE", "")
    
    # 图标配置
    BUY_ICON_URL: str = os.getenv(
        "BUY_ICON_URL",
        "https://raw.githubusercontent.com/SoftwarePianist/sbPush/main/assets/buy_icon.png"
    )
    SELL_ICON_URL: str = os.getenv(
        "SELL_ICON_URL",
        "https://raw.githubusercontent.com/SoftwarePianist/sbPush/main/assets/sell_icon.png"
    )
    
    @classmethod
    def get_notifier_config(cls) -> Dict[str, Dict[str, Any]]:
        """
        获取所有推送渠道的配置
        
        Returns:
            格式: {
                "server_chan": {"enabled": True, "push_key": "xxx"},
                "bark": {"enabled": False, "device_key": "xxx"},
                ...
            }
        """
        notifiers = {}
        
        # Server酱配置
        notifiers["server_chan"] = {
            "enabled": _get_bool("NOTIFIER_SERVER_CHAN_ENABLED"),
            "push_key": os.getenv("NOTIFIER_SERVER_CHAN_PUSH_KEY", ""),
        }
        
        # Bark配置
        notifiers["bark"] = {
            "enabled": _get_bool("NOTIFIER_BARK_ENABLED"),
            "device_key": os.getenv("NOTIFIER_BARK_DEVICE_KEY", ""),
            "server": os.getenv("NOTIFIER_BARK_SERVER", "https://api.day.app"),
            "group": os.getenv("NOTIFIER_BARK_GROUP", "股票监控"),
            "sound": os.getenv("NOTIFIER_BARK_SOUND", "default"),
        }
        
        # PushPlus配置
        notifiers["pushplus"] = {
            "enabled": _get_bool("NOTIFIER_PUSHPLUS_ENABLED"),
            "token": os.getenv("NOTIFIER_PUSHPLUS_TOKEN", ""),
            "channel": os.getenv("NOTIFIER_PUSHPLUS_CHANNEL", "wechat"),
            "template": os.getenv("NOTIFIER_PUSHPLUS_TEMPLATE", "markdown"),
        }
        
        # 钉钉配置
        notifiers["dingtalk"] = {
            "enabled": _get_bool("NOTIFIER_DINGTALK_ENABLED"),
            "webhook": os.getenv("NOTIFIER_DINGTALK_WEBHOOK", ""),
        }
        
        return notifiers
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否存在"""
        notifier_config = cls.get_notifier_config()
        has_enabled = any(
            cfg.get("enabled", False) 
            for cfg in notifier_config.values()
        )
        
        if not has_enabled:
            print("⚠️  警告: 未启用任何推送渠道，将无法发送通知")
            print("💡 请在 config/.env 中配置至少一个推送渠道")
            return False
        
        return True


# 全局配置实例
config = Config()
