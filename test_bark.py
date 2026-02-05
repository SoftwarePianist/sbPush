#!/usr/bin/env python3
"""
测试 Bark 推送 - 抓取调仓记录并推送
"""
import sys
sys.path.insert(0, '.')

from src.scraper import PageScraper
from src.notifier import BarkNotifier

# 配置 Bark
bark_config = {
    "enabled": True,
    "device_key": "iDYarbHCbhNYp4En2TUUke",
    "group": "调仓监控",
}

# 1. 抓取页面内容（结构化）
print("🔍 正在抓取调仓记录...")
with PageScraper() as scraper:
    data = scraper.get_latest_record_structured()

if data:
    print(f"✅ 抓取成功")
    print("-" * 50)
    print(data)
    print("-" * 50)
    
    # 2. 格式化推送内容
    trade_type = data.get("trade_type", "")
    stock_code = data.get("stock_code", "")
    position_change = data.get("position_change", "")
    price = data.get("price", "")
    
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
    # 价格和仓位放在同一行
    price_position = []
    if price:
        price_position.append(price)
    if position_change:
        price_position.append(position_change)
    if price_position:
        content_lines.append(" | ".join(price_position))
    
    content = "\n".join(content_lines)
    
    print(f"\n📱 推送标题: {title}")
    print(f"📱 推送内容: {content}")
    print(f"📱 推送图标: {icon}")
    
    # 3. 推送到 Bark
    print("\n📱 正在推送到 Bark...")
    notifier = BarkNotifier(bark_config)
    result = notifier.send(title=title, content=content, icon=icon)
    print(f"推送结果: {result}")
else:
    print("❌ 抓取失败，无法获取内容")
