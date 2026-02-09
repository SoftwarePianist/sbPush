"""
监控核心模块
持续监控页面变化并发送通知
"""
import time
from datetime import datetime, timedelta
from typing import Optional
from .config import config
from .scraper import PageScraper
from .notifier import NotifierManager, init_notifiers
from .logger import get_logger, print_startup_banner, print_config_summary
from croniter import croniter
import pytz


class StockMonitor:
    """股票组合调仓监控器"""
    
    def __init__(self):
        self.scraper = PageScraper()
        self.notifier_manager: Optional[NotifierManager] = None
        self.last_record: Optional[str] = None
        self.check_count: int = 0
        self.logger = get_logger()
        self.start_time: Optional[datetime] = None
    
    def _log(self, message: str, level: str = "info") -> None:
        """日志输出"""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    def _init_notifiers(self) -> None:
        """初始化推送管理器"""
        notifier_config = config.get_notifier_config()
        self.notifier_manager = init_notifiers(notifier_config)
        
        if self.notifier_manager.channels:
            self._log(f"📢 已启用推送渠道: {', '.join(self.notifier_manager.channels)}")
        else:
            self._log("⚠️  未配置任何推送渠道", "warning")
    
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
            # 图标 URL 从配置中获取，支持自定义
            if "买" in trade_type:
                title = "🟢 买入"
                icon = config.BUY_ICON_URL
            elif "卖" in trade_type:
                title = "🔴 卖出"
                icon = config.SELL_ICON_URL
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
                # 获取详情页 URL（点击理由跳转的页面）
                detail_url = current_record.get("detail_url", "") or config.TARGET_URL
                # 对于 Bark 渠道，传入图标和点击跳转 URL；其他渠道忽略
                for notifier in self.notifier_manager._notifiers:
                    if notifier.channel_name == "bark":
                        notifier.send(title, content, icon=icon, url=detail_url)
                    else:
                        notifier.send(title, content)
            
            self.last_record = record_key
            return True
        
        self._log("✓ 无变化", "debug")
        return False
    
    def run(self) -> None:
        """启动持续监控（主线程调度，避免 Playwright greenlet 问题）"""
        self.start_time = datetime.now()
        
        # 打印启动横幅和配置摘要
        print_startup_banner()
        print_config_summary(self.logger)
        
        # 验证配置
        config.validate()
        
        # 初始化推送
        self._init_notifiers()
        
        try:
            self.scraper.start()
            
            # 明确指定时区
            tz = pytz.timezone('Asia/Shanghai')
            
            # 启动时先执行一次
            self.check_once()
            
            if config.CHECK_CRON:
                self._log(f"⏱️  使用 Cron 调度: {config.CHECK_CRON}")
                self._run_with_cron(tz)
            else:
                self._log(f"⏱️  使用固定间隔调度: {config.CHECK_INTERVAL} 秒")
                self._run_with_interval()
            
        except KeyboardInterrupt:
            self._log("⏹️  收到停止信号", "warning")
        except Exception as e:
            self._log(f"❌ 运行出错: {e}", "error")
            import traceback
            traceback.print_exc()
        finally:
            self.scraper.stop()
            uptime = datetime.now() - self.start_time if self.start_time else None
            if uptime:
                hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self._log(f"👋 监控服务已停止 (运行时长: {hours}小时{minutes}分{seconds}秒)")
            else:
                self._log("👋 监控服务已停止")
    
    def _run_with_interval(self) -> None:
        """使用固定间隔运行（主线程循环）"""
        while True:
            self._log("⏳ 等待下次调度...")
            time.sleep(config.CHECK_INTERVAL)
            self.check_once()
    
    def _run_with_cron(self, tz) -> None:
        """使用 Cron 表达式运行（主线程循环）"""
        cron_expr = config.CHECK_CRON
        cron_parts = cron_expr.split()
        
        # croniter 只支持 5 字段标准格式，6 字段需要转换
        if len(cron_parts) == 6:
            # 6 字段格式: 秒 分 时 日 月 周
            # 提取秒字段，转换为 5 字段格式
            second_expr = cron_parts[0]
            cron_5_field = " ".join(cron_parts[1:])  # 分 时 日 月 周
            
            # 解析秒字段以确定间隔
            if second_expr.startswith("*/"):
                second_interval = int(second_expr[2:])
            elif second_expr == "*":
                second_interval = 1
            else:
                # 固定秒数
                second_interval = None
                target_second = int(second_expr)
        else:
            # 标准 5 字段格式: 分 时 日 月 周
            cron_5_field = cron_expr
            second_interval = None
            target_second = 0
        
        self._log(f"⏳ 等待下次调度...")
        
        while True:
            now = datetime.now(tz)
            cron = croniter(cron_5_field, now)
            next_run = cron.get_next(datetime)
            
            # 如果有秒级调度
            if len(cron_parts) == 6:
                if second_interval:
                    # 计算下一个符合条件的时间点
                    # 如果当前分钟符合条件，计算本分钟内的下个触发点
                    current_second = now.second
                    if second_interval:
                        # 找到本分钟内下一个触发秒数
                        next_second_in_minute = ((current_second // second_interval) + 1) * second_interval
                        if next_second_in_minute < 60:
                            # 本分钟内还有触发点，检查是否在调度时间范围内
                            potential_time = now.replace(second=next_second_in_minute, microsecond=0)
                            # 使用 croniter 检查这个时间点是否匹配（忽略秒）
                            check_cron = croniter(cron_5_field, potential_time - timedelta(minutes=1))
                            check_next = check_cron.get_next(datetime)
                            if check_next.replace(second=0) == potential_time.replace(second=0):
                                next_run = potential_time
                            else:
                                # 等待下一个匹配的分钟
                                next_run = cron.get_next(datetime).replace(second=0)
                        else:
                            # 需要等到下一分钟
                            next_run = cron.get_next(datetime).replace(second=0)
                else:
                    # 固定秒数
                    next_run = next_run.replace(second=target_second)
            
            wait_seconds = (next_run - now).total_seconds()
            if wait_seconds > 0:
                self._log(f"⏳ 下次执行: {next_run.strftime('%H:%M:%S')} (等待 {wait_seconds:.0f} 秒)")
                time.sleep(wait_seconds)
            
            self.check_once()


def run_monitor():
    """启动监控（便捷函数）"""
    monitor = StockMonitor()
    monitor.run()
