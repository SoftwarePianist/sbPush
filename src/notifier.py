"""
消息推送模块
支持多种推送渠道，可扩展设计（开闭原则）

使用方法：
    1. 继承 BaseNotifier 实现新的推送渠道
    2. 使用 @NotifierRegistry.register 装饰器注册
    3. 在配置中启用对应渠道
"""
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type
from dataclasses import dataclass


@dataclass
class NotifyResult:
    """推送结果"""
    success: bool
    channel: str
    message: str = ""


class BaseNotifier(ABC):
    """
    推送器基类
    所有推送渠道都需要继承此类并实现 send 方法
    """
    
    # 渠道名称，子类需要覆盖
    channel_name: str = "base"
    
    def __init__(self, config: Dict):
        """
        初始化推送器
        
        Args:
            config: 该渠道的配置字典
        """
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def send(self, title: str, content: str = "") -> NotifyResult:
        """
        发送推送
        
        Args:
            title: 推送标题
            content: 推送内容（支持 Markdown）
        
        Returns:
            NotifyResult: 推送结果
        """
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效，子类可覆盖"""
        return True


class NotifierRegistry:
    """
    推送器注册表
    使用装饰器模式自动注册推送器
    """
    _notifiers: Dict[str, Type[BaseNotifier]] = {}
    
    @classmethod
    def register(cls, name: str):
        """
        注册推送器的装饰器
        
        Usage:
            @NotifierRegistry.register("server_chan")
            class ServerChanNotifier(BaseNotifier):
                ...
        """
        def decorator(notifier_class: Type[BaseNotifier]):
            cls._notifiers[name] = notifier_class
            notifier_class.channel_name = name
            return notifier_class
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseNotifier]]:
        """获取已注册的推送器类"""
        return cls._notifiers.get(name)
    
    @classmethod
    def all(cls) -> Dict[str, Type[BaseNotifier]]:
        """获取所有已注册的推送器"""
        return cls._notifiers.copy()
    
    @classmethod
    def available_channels(cls) -> List[str]:
        """获取所有可用渠道名称"""
        return list(cls._notifiers.keys())


# ============================================================
# 具体推送器实现
# ============================================================

@NotifierRegistry.register("server_chan")
class ServerChanNotifier(BaseNotifier):
    """
    Server酱推送
    官网: https://sct.ftqq.com
    """
    
    BASE_URL = "https://sctapi.ftqq.com"
    
    def validate_config(self) -> bool:
        return bool(self.config.get("push_key"))
    
    def send(self, title: str, content: str = "") -> NotifyResult:
        push_key = self.config.get("push_key")
        
        if not push_key:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message="未配置 push_key"
            )
        
        url = f"{self.BASE_URL}/{push_key}.send"
        data = {
            "title": title[:256],
            "desp": content
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                return NotifyResult(
                    success=True,
                    channel=self.channel_name,
                    message="推送成功"
                )
            else:
                return NotifyResult(
                    success=False,
                    channel=self.channel_name,
                    message=result.get("message", "未知错误")
                )
                
        except requests.RequestException as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"网络请求失败: {e}"
            )
        except Exception as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"推送异常: {e}"
            )


@NotifierRegistry.register("bark")
class BarkNotifier(BaseNotifier):
    """
    Bark 推送（iOS），支持多用户
    官网: https://github.com/Finb/Bark
    """
    
    DEFAULT_SERVER = "https://api.day.app"
    
    def _get_device_keys(self) -> List[str]:
        """获取设备密钥列表（支持逗号分隔的多个密钥）"""
        device_key = self.config.get("device_key", "")
        if not device_key:
            return []
        # 支持逗号分隔的多个 device_key
        keys = [k.strip() for k in device_key.split(",") if k.strip()]
        return keys
    
    def validate_config(self) -> bool:
        return len(self._get_device_keys()) > 0
    
    def _send_to_device(self, device_key: str, title: str, content: str, icon: str = None) -> tuple:
        """向单个设备发送推送，返回 (success, message)"""
        server = self.config.get("server", self.DEFAULT_SERVER).rstrip("/")
        url = f"{server}/{device_key}"
        
        # Bark 支持的参数
        params = {
            "title": title,
            "body": content,
            "group": self.config.get("group", "股票监控"),
            "sound": self.config.get("sound", "default"),
        }
        
        # 动态图标优先，否则使用配置中的图标
        if icon:
            params["icon"] = icon
        elif self.config.get("icon"):
            params["icon"] = self.config["icon"]
        
        # 可选：点击跳转 URL
        if self.config.get("url"):
            params["url"] = self.config["url"]
        
        try:
            response = requests.post(url, json=params, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                return True, "成功"
            else:
                return False, result.get("message", "未知错误")
                
        except requests.RequestException as e:
            return False, f"网络请求失败: {e}"
        except Exception as e:
            return False, f"推送异常: {e}"
    
    def send(self, title: str, content: str = "", icon: str = None) -> NotifyResult:
        device_keys = self._get_device_keys()
        
        if not device_keys:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message="未配置 device_key"
            )
        
        # 向所有设备发送推送
        success_count = 0
        fail_count = 0
        fail_messages = []
        
        for i, device_key in enumerate(device_keys, 1):
            success, msg = self._send_to_device(device_key, title, content, icon)
            if success:
                success_count += 1
            else:
                fail_count += 1
                # 只显示设备序号，不暴露完整 key
                fail_messages.append(f"设备{i}: {msg}")
        
        total = len(device_keys)
        
        if success_count == total:
            return NotifyResult(
                success=True,
                channel=self.channel_name,
                message=f"推送成功 ({success_count}/{total} 设备)"
            )
        elif success_count > 0:
            return NotifyResult(
                success=True,  # 部分成功也算成功
                channel=self.channel_name,
                message=f"部分成功 ({success_count}/{total} 设备), 失败: {'; '.join(fail_messages)}"
            )
        else:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"全部失败 ({fail_count} 设备): {'; '.join(fail_messages)}"
            )


@NotifierRegistry.register("pushplus")
class PushPlusNotifier(BaseNotifier):
    """
    PushPlus 推送
    官网: https://www.pushplus.plus
    支持微信公众号、企业微信等多种渠道
    """
    
    BASE_URL = "https://www.pushplus.plus/send"
    
    def validate_config(self) -> bool:
        return bool(self.config.get("token"))
    
    def send(self, title: str, content: str = "") -> NotifyResult:
        token = self.config.get("token")
        
        if not token:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message="未配置 token"
            )
        
        data = {
            "token": token,
            "title": title,
            "content": content,
            "template": self.config.get("template", "markdown"),
            "channel": self.config.get("channel", "wechat"),
        }
        
        # 可选：topic（群组编码）
        if self.config.get("topic"):
            data["topic"] = self.config["topic"]
        
        try:
            response = requests.post(self.BASE_URL, json=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                return NotifyResult(
                    success=True,
                    channel=self.channel_name,
                    message="推送成功"
                )
            else:
                return NotifyResult(
                    success=False,
                    channel=self.channel_name,
                    message=result.get("msg", "未知错误")
                )
                
        except requests.RequestException as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"网络请求失败: {e}"
            )
        except Exception as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"推送异常: {e}"
            )


@NotifierRegistry.register("dingtalk")
class DingTalkNotifier(BaseNotifier):
    """
    钉钉机器人推送
    文档: https://open.dingtalk.com/document/robots/custom-robot-access
    """
    
    def validate_config(self) -> bool:
        return bool(self.config.get("webhook"))
    
    def send(self, title: str, content: str = "") -> NotifyResult:
        webhook = self.config.get("webhook")
        
        if not webhook:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message="未配置 webhook"
            )
        
        # 钉钉 Markdown 消息格式
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{content}"
            }
        }
        
        try:
            response = requests.post(
                webhook,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            result = response.json()
            
            if result.get("errcode") == 0:
                return NotifyResult(
                    success=True,
                    channel=self.channel_name,
                    message="推送成功"
                )
            else:
                return NotifyResult(
                    success=False,
                    channel=self.channel_name,
                    message=result.get("errmsg", "未知错误")
                )
                
        except requests.RequestException as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"网络请求失败: {e}"
            )
        except Exception as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"推送异常: {e}"
            )


# ============================================================
# 推送管理器
# ============================================================

class NotifierManager:
    """
    推送管理器
    统一管理多个推送渠道，支持同时推送到多个渠道
    """
    
    def __init__(self):
        self._notifiers: List[BaseNotifier] = []
    
    def add(self, notifier: BaseNotifier) -> "NotifierManager":
        """添加推送器"""
        if notifier.enabled and notifier.validate_config():
            self._notifiers.append(notifier)
            print(f"✅ 已启用推送渠道: {notifier.channel_name}")
        return self
    
    def add_by_name(self, name: str, config: Dict) -> "NotifierManager":
        """通过渠道名称添加推送器"""
        notifier_class = NotifierRegistry.get(name)
        if notifier_class:
            notifier = notifier_class(config)
            self.add(notifier)
        else:
            print(f"⚠️  未知的推送渠道: {name}")
        return self
    
    def send_all(self, title: str, content: str = "") -> List[NotifyResult]:
        """
        向所有已启用的渠道发送推送
        
        Returns:
            所有渠道的推送结果列表
        """
        results = []
        
        if not self._notifiers:
            print("⚠️  没有配置任何推送渠道")
            return results
        
        for notifier in self._notifiers:
            result = notifier.send(title, content)
            results.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"{status} [{result.channel}] {result.message}")
        
        return results
    
    def send_any(self, title: str, content: str = "") -> bool:
        """发送推送，只要有一个渠道成功即返回 True"""
        results = self.send_all(title, content)
        return any(r.success for r in results)
    
    @property
    def channels(self) -> List[str]:
        """获取已启用的渠道列表"""
        return [n.channel_name for n in self._notifiers]
    
    @classmethod
    def from_config(cls, config: Dict) -> "NotifierManager":
        """
        从配置字典创建管理器
        
        配置格式:
        {
            "server_chan": {"enabled": True, "push_key": "xxx"},
            "bark": {"enabled": True, "device_key": "xxx"},
            ...
        }
        """
        manager = cls()
        
        for channel_name, channel_config in config.items():
            if channel_config.get("enabled", True):
                manager.add_by_name(channel_name, channel_config)
        
        return manager


# ============================================================
# 便捷函数（向后兼容）
# ============================================================

# 默认管理器实例
_default_manager: Optional[NotifierManager] = None


def init_notifiers(config: Dict) -> NotifierManager:
    """初始化推送管理器"""
    global _default_manager
    _default_manager = NotifierManager.from_config(config)
    return _default_manager


def get_manager() -> NotifierManager:
    """获取默认管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = NotifierManager()
    return _default_manager


def send_notification(title: str, content: str = "") -> bool:
    """
    便捷函数：发送通知到所有已配置的渠道
    
    Returns:
        bool: 是否至少有一个渠道发送成功
    """
    return get_manager().send_any(title, content)
