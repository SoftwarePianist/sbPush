"""
监控核心模块
持续监控页面变化并发送通知
"""
import time
from datetime import datetime
from typing import Optional
from .config import config
from .scraper import PageScraper
from .notifier import NotifierManager, init_notifiers


class StockMonitor:
    """股票组合调仓监控器"""
    
    def __init__(self):
        self.scraper = PageScraper()
        self.notifier_manager: Optional[NotifierManager] = None
        self.last_record: Optional[str] = None
        self.check_count: int = 0
    
    def _log(self, message: str) -> None:
        """带时间戳的日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def _init_notifiers(self) -> None:
        """初始化推送管理器"""
        notifier_config = config.get_notifier_config()
        self.notifier_manager = init_notifiers(notifier_config)
        
        if self.notifier_manager.channels:
            self._log(f"📢 已启用推送渠道: {', '.join(self.notifier_manager.channels)}")
        else:
            self._log("⚠️  未配置任何推送渠道")
    
    def check_once(self) -> bool:
        """
        执行一次检查
        
        Returns:
            bool: 是否检测到更新
        """
        self.check_count += 1
        self._log(f"第 {self.check_count} 次检查...")
        
        current_record = self.scraper.get_latest_record_structured()
        
        if not current_record:
            self._log("⚠️  未能获取到数据，请检查选择器或网络")
            return False
        
        # 生成用于比较的唯一标识（股票代码+时间+类型）
        record_key = f"{current_record.get('stock_code')}|{current_record.get('trade_time')}|{current_record.get('trade_type')}"
        
        # 首次运行，记录当前状态
        if self.last_record is None:
            self.last_record = record_key
            self._log("📝 已记录初始状态")
            self._log(f"当前记录: {current_record.get('stock_code')} {current_record.get('trade_type')}")
            return False
        
        # 检测变化
        if record_key != self.last_record:
            self._log("🎉 检测到新调仓！")
            
            # 格式化推送内容（与 test_bark.py 一致）
            trade_type = current_record.get("trade_type", "")
            stock_code = current_record.get("stock_code", "")
            position_change = current_record.get("position_change", "")
            price = current_record.get("price", "")
            
            # 标题和图标：买入/卖出
            # 使用 GitHub Raw 托管的自定义图标
            if "买" in trade_type:
                title = "🟢 买入"
                icon = "https://raw.githubusercontent.com/SoftwarePianist/sbPush/main/assets/buy_icon.png"
            elif "卖" in trade_type:
                title = "🔴 卖出"
                icon = "https://raw.githubusercontent.com/SoftwarePianist/sbPush/main/assets/sell_icon.png"
            else:
                title = f"📈 {trade_type}"
                icon = None
            
            # 内容：股票代码，价格+仓位（同一行）
            content_lines = []
            if stock_code:
                content_lines.append(stock_code)
            price_position = []
            if price:
                price_position.append(price)
            if position_change:
                price_position.append(position_change)
            if price_position:
                content_lines.append(" | ".join(price_position))
            
            content = "\n".join(content_lines)
            
            if self.notifier_manager:
                # 对于 Bark 渠道，传入图标；其他渠道忽略
                for notifier in self.notifier_manager._notifiers:
                    if notifier.channel_name == "bark":
                        notifier.send(title, content, icon=icon)
                    else:
                        notifier.send(title, content)
            
            self.last_record = record_key
            return True
        
        self._log("✓ 无变化")
        return False
    
    def run(self) -> None:
        """启动持续监控"""
        self._log("🚀 监控服务启动")
        self._log(f"📍 目标URL: {config.TARGET_URL}")
        self._log(f"⏱️  检查间隔: {config.CHECK_INTERVAL} 秒")
        
        # 验证配置
        config.validate()
        
        # 初始化推送
        self._init_notifiers()
        
        try:
            self.scraper.start()
            
            while True:
                try:
                    self.check_once()
                except Exception as e:
                    self._log(f"❌ 检查出错: {e}")
                
                time.sleep(config.CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            self._log("⏹️  收到停止信号")
        finally:
            self.scraper.stop()
            self._log("👋 监控服务已停止")


def run_monitor():
    """启动监控（便捷函数）"""
    monitor = StockMonitor()
    monitor.run()
