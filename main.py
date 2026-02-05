#!/usr/bin/env python3
"""
平安证券组合调仓监控
主入口文件
"""
import argparse
import sys
from src.monitor import run_monitor, StockMonitor
from src.scraper import PageScraper
from src.notifier import NotifierManager, NotifierRegistry
from src.config import config


def cmd_monitor(args):
    """启动监控服务"""
    run_monitor()


def cmd_test(args):
    """测试抓取功能"""
    print("🧪 测试模式：获取页面内容")
    print(f"📍 目标URL: {config.TARGET_URL}")
    print("-" * 50)
    
    with PageScraper() as scraper:
        record = scraper.get_latest_record()
        
        if record:
            print("✅ 成功获取到内容：")
            print("-" * 50)
            print(record)
            print("-" * 50)
            
            if args.screenshot:
                scraper.screenshot("debug_screenshot.png")
        else:
            print("❌ 未能获取到内容")
            print("💡 建议：")
            print("   1. 检查网络连接")
            print("   2. 在 src/scraper.py 中调整 RECORD_SELECTORS")
            print("   3. 使用 --screenshot 参数保存截图进行分析")
            
            if args.screenshot:
                scraper.screenshot("debug_screenshot.png")


def cmd_push_test(args):
    """测试推送功能"""
    print("🧪 测试推送...")
    print("-" * 50)
    
    # 获取推送配置
    notifier_config = config.get_notifier_config()
    
    # 显示所有可用渠道
    print("📋 可用推送渠道:")
    for channel in NotifierRegistry.available_channels():
        print(f"   - {channel}")
    print()
    
    # 显示已配置的渠道状态
    print("📋 渠道配置状态:")
    for channel, cfg in notifier_config.items():
        status = "✅ 已启用" if cfg.get("enabled") else "⬚ 未启用"
        print(f"   {status} {channel}")
    print()
    
    # 初始化并发送测试消息
    manager = NotifierManager.from_config(notifier_config)
    
    if not manager.channels:
        print("❌ 未启用任何推送渠道")
        print("💡 请在 config/.env 文件中启用至少一个推送渠道")
        sys.exit(1)
    
    print(f"📤 向以下渠道发送测试消息: {', '.join(manager.channels)}")
    print("-" * 50)
    
    results = manager.send_all(
        "🧪 测试推送",
        "这是一条测试消息，说明推送功能正常工作！\n\n*来自 sbPush 监控服务*"
    )
    
    # 统计结果
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    
    print("-" * 50)
    print(f"📊 推送结果: {success_count}/{total_count} 成功")
    
    if success_count == 0:
        sys.exit(1)


def cmd_debug(args):
    """调试模式：显示浏览器窗口"""
    print("🔍 调试模式：将显示浏览器窗口")
    
    # 临时禁用无头模式
    original_headless = config.HEADLESS
    config.HEADLESS = False
    
    try:
        with PageScraper() as scraper:
            print("📄 正在加载页面...")
            record = scraper.get_latest_record()
            
            if record:
                print("✅ 获取到内容：")
                print(record[:200])
            
            scraper.screenshot("debug_screenshot.png")
            
            print("\n💡 提示：查看 debug_screenshot.png 截图")
            print("💡 按 Ctrl+C 退出")
            
            # 保持浏览器打开一段时间供调试
            import time
            time.sleep(30)
            
    finally:
        config.HEADLESS = original_headless


def cmd_channels(args):
    """列出所有可用的推送渠道"""
    print("📋 所有可用的推送渠道:")
    print("-" * 50)
    
    for channel in NotifierRegistry.available_channels():
        notifier_class = NotifierRegistry.get(channel)
        if notifier_class:
            doc = notifier_class.__doc__ or "无描述"
            # 取第一行作为简介
            brief = doc.strip().split("\n")[0].strip()
            print(f"  {channel:<15} {brief}")
    
    print("-" * 50)
    print("💡 在 config/.env 中设置 NOTIFIER_<CHANNEL>_ENABLED=true 启用对应渠道")


def main():
    parser = argparse.ArgumentParser(
        description="平安证券组合调仓监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py monitor        # 启动监控服务
  python main.py test           # 测试抓取功能
  python main.py test -s        # 测试抓取并保存截图
  python main.py push-test      # 测试所有已配置的推送渠道
  python main.py channels       # 列出所有可用推送渠道
  python main.py debug          # 调试模式（显示浏览器）
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # monitor 命令
    parser_monitor = subparsers.add_parser("monitor", help="启动监控服务")
    parser_monitor.set_defaults(func=cmd_monitor)
    
    # test 命令
    parser_test = subparsers.add_parser("test", help="测试抓取功能")
    parser_test.add_argument(
        "-s", "--screenshot",
        action="store_true",
        help="保存页面截图"
    )
    parser_test.set_defaults(func=cmd_test)
    
    # push-test 命令
    parser_push = subparsers.add_parser("push-test", help="测试推送功能")
    parser_push.set_defaults(func=cmd_push_test)
    
    # channels 命令
    parser_channels = subparsers.add_parser("channels", help="列出所有可用推送渠道")
    parser_channels.set_defaults(func=cmd_channels)
    
    # debug 命令
    parser_debug = subparsers.add_parser("debug", help="调试模式")
    parser_debug.set_defaults(func=cmd_debug)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
