"""
日志模块
提供统一的日志管理功能
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import config


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m',      # 重置
    }
    
    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(
    name: str = "sbpush",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 可选的日志文件路径
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = ColoredFormatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def print_startup_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   📈 sbPush 监控服务启动                      ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_config_summary(logger: logging.Logger):
    """打印配置摘要"""
    logger.info("=" * 60)
    logger.info("📋 配置摘要")
    logger.info("-" * 60)
    
    # 监控配置
    logger.info(f"🎯 目标 URL: {config.TARGET_URL}")
    
    if config.CHECK_CRON:
        logger.info(f"⏰ 检查计划: Cron 表达式 [{config.CHECK_CRON}]")
    else:
        logger.info(f"⏰ 检查间隔: {config.CHECK_INTERVAL} 秒")
    
    logger.info(f"🖥️  无头模式: {'是' if config.HEADLESS else '否（显示浏览器）'}")
    
    # 推送配置
    notifier_config = config.get_notifier_config()
    enabled_channels = [name for name, cfg in notifier_config.items() if cfg.get("enabled")]
    
    if enabled_channels:
        logger.info(f"📢 推送渠道: {', '.join(enabled_channels)}")
    else:
        logger.warning("⚠️  未启用任何推送渠道")
    
    # Cookie 配置
    if config.COOKIES_FILE:
        from pathlib import Path
        cookies_path = Path(config.COOKIES_FILE)
        if cookies_path.exists():
            logger.info(f"🍪 Cookie 文件: {config.COOKIES_FILE} ✓")
        else:
            logger.warning(f"⚠️  Cookie 文件不存在: {config.COOKIES_FILE}")
    elif config.COOKIES:
        logger.info("🍪 Cookie: 从环境变量加载")
    else:
        logger.warning("⚠️  未配置 Cookie，可能无法获取完整数据")
    
    logger.info("=" * 60)


# 全局日志记录器
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """获取全局日志记录器"""
    global _logger
    if _logger is None:
        # 从环境变量获取日志级别，默认 INFO
        import os
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file = os.getenv("LOG_FILE", None)
        _logger = setup_logger(level=log_level, log_file=log_file)
    return _logger
