"""
网页抓取模块
使用 Playwright 模拟浏览器访问动态渲染页面
"""
import json
from pathlib import Path
from typing import Optional, List
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from .config import config


class PageScraper:
    """页面抓取器"""
    
    # 调仓记录选择器
    RECORD_SELECTORS = [
        ".record-invest-outside",
    ]
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    def _parse_raw_cookie_string(self, cookie_string: str, domain: str = "m.stock.pingan.com") -> List[dict]:
        """
        解析从浏览器 F12 复制的原始 cookie 字符串
        
        格式: name=value; name2=value2; ...
        
        Args:
            cookie_string: 原始 cookie 字符串
            domain: Cookie 的域名，默认为目标域名
        
        Returns:
            Cookie 列表 (Playwright 格式)
        """
        cookies = []
        # 按分号分割
        pairs = cookie_string.split(';')
        for pair in pairs:
            pair = pair.strip()
            if not pair or '=' not in pair:
                continue
            # 只分割第一个等号，因为 value 中可能包含等号
            name, value = pair.split('=', 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                })
        return cookies
    
    def _load_cookies(self) -> List[dict]:
        """
        加载 Cookies 配置
        支持两种方式:
        1. COOKIES 环境变量: JSON 格式的 cookie 数组，或原始 cookie 字符串 (name=value; name2=value2)
        2. COOKIES_FILE 环境变量: 指向 cookies.json 或 cookies.txt 文件的路径
        
        Returns:
            Cookie 列表
        """
        raw_cookies = []
        
        # 优先从文件加载
        if config.COOKIES_FILE:
            cookies_path = Path(config.COOKIES_FILE)
            if cookies_path.exists():
                try:
                    with open(cookies_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    # 尝试解析为 JSON
                    if content.startswith('['):
                        raw_cookies = json.loads(content)
                        print(f"🍪 从文件加载了 {len(raw_cookies)} 个 cookies (JSON 格式)")
                    else:
                        # 解析原始 cookie 字符串格式: name=value; name2=value2
                        raw_cookies = self._parse_raw_cookie_string(content)
                        print(f"🍪 从文件加载了 {len(raw_cookies)} 个 cookies (原始字符串格式)")
                except Exception as e:
                    print(f"⚠️ 加载 cookies 文件失败: {e}")
            else:
                print(f"⚠️ cookies 文件不存在: {cookies_path}")
        
        # 如果文件不存在，尝试从环境变量加载
        elif config.COOKIES:
            try:
                # 尝试解析为 JSON
                if config.COOKIES.strip().startswith('['):
                    raw_cookies = json.loads(config.COOKIES)
                    print(f"🍪 从环境变量加载了 {len(raw_cookies)} 个 cookies (JSON 格式)")
                else:
                    # 解析原始 cookie 字符串格式
                    raw_cookies = self._parse_raw_cookie_string(config.COOKIES)
                    print(f"🍪 从环境变量加载了 {len(raw_cookies)} 个 cookies (原始字符串格式)")
            except Exception as e:
                print(f"⚠️ 解析 cookies 失败: {e}")
        
        # 处理 cookies，修复 sameSite 等字段
        cookies = []
        valid_same_site = {"Strict", "Lax", "None"}
        # 目标域名
        target_domains = ["m.stock.pingan.com", ".pingan.com", ".stock.pingan.com"]
        
        for cookie in raw_cookies:
            domain = cookie.get("domain", "")
            
            # 只保留与目标域名相关的 cookies
            if not any(domain.endswith(d.lstrip('.')) or d.endswith(domain.lstrip('.')) for d in target_domains):
                continue
            
            # 只保留 Playwright 支持的字段
            clean_cookie = {
                "name": cookie.get("name"),
                "value": cookie.get("value"),
                "domain": domain,
                "path": cookie.get("path", "/"),
            }
            # 处理 sameSite
            same_site = cookie.get("sameSite", "Lax")
            if same_site not in valid_same_site:
                same_site = "Lax"  # 默认使用 Lax
            clean_cookie["sameSite"] = same_site
            
            # 可选字段
            if cookie.get("secure"):
                clean_cookie["secure"] = cookie["secure"]
            # 处理过期时间 (EditThisCookie 导出的是 expirationDate，Playwright 需要 expires)
            if cookie.get("expires"):
                clean_cookie["expires"] = cookie["expires"]
            elif cookie.get("expirationDate"):
                clean_cookie["expires"] = cookie["expirationDate"]
            
            cookies.append(clean_cookie)
        
        # 打印实际加载的 cookies 数量 (调试用)
        login_cookies = [c for c in cookies if 'login' in c.get('name', '').lower()]
        if login_cookies:
            print(f"🔑 检测到 {len(login_cookies)} 个登录相关 cookies")
        
        return cookies
    
    def start(self) -> None:
        """启动浏览器"""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=config.HEADLESS
        )
        self._context = self._browser.new_context(
            user_agent=config.USER_AGENT,
            viewport={"width": 375, "height": 812},  # iPhone X 尺寸
        )
        
        # 加载并注入 cookies
        cookies = self._load_cookies()
        if cookies:
            self._context.add_cookies(cookies)
        
        self._page = self._context.new_page()
        self._page.set_default_timeout(config.PAGE_TIMEOUT)
        print("🌐 浏览器已启动")
    
    def stop(self) -> None:
        """关闭浏览器"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        print("🌐 浏览器已关闭")
    
    def get_latest_record(self, url: Optional[str] = None) -> Optional[str]:
        """
        获取页面第一条调仓记录
        
        Args:
            url: 目标 URL，默认使用配置中的 URL
        
        Returns:
            第一条记录的文本内容，获取失败返回 None
        """
        target_url = url or config.TARGET_URL
        
        if not self._page:
            print("❌ 浏览器未启动")
            return None
        
        try:
            # 导航到目标页面
            self._page.goto(target_url, wait_until="networkidle")
            
            # 额外等待 JS 渲染完成
            self._page.wait_for_timeout(config.RENDER_WAIT)
            
            # 尝试不同的选择器
            for selector in self.RECORD_SELECTORS:
                items = self._page.locator(selector)
                if items.count() > 0:
                    first_record = items.first.inner_text()
                    if first_record.strip():
                        print(f"📄 使用选择器: {selector}")
                        return first_record.strip()
            
            # 如果所有选择器都失败，尝试获取页面主要内容
            print("⚠️  未找到匹配的选择器，尝试获取页面主体内容")
            body_text = self._page.locator("body").inner_text()
            return body_text[:500] if body_text else None
            
        except Exception as e:
            print(f"❌ 抓取出错: {e}")
            return None
    
    def get_latest_record_structured(self, url: Optional[str] = None) -> Optional[dict]:
        """
        获取页面第一条调仓记录（结构化数据）
        
        Returns:
            包含以下字段的字典：
            - trade_type: "买" 或 "卖"
            - stock_code: 股票代码
            - position_change: 仓位变化
            - trade_time: 调仓时间
            - reason: 操作理由
        """
        target_url = url or config.TARGET_URL
        
        if not self._page:
            print("❌ 浏览器未启动")
            return None
        
        try:
            self._page.goto(target_url, wait_until="networkidle")
            self._page.wait_for_timeout(config.RENDER_WAIT)
            
            record = self._page.locator(".record-invest-outside").first
            if record.count() == 0:
                print("⚠️ 未找到调仓记录")
                return None
            
            # 提取买卖类型 (在 .stock-sale-icon span 中)
            trade_icon = record.locator(".stock-sale-icon span")
            trade_type = trade_icon.inner_text().strip() if trade_icon.count() > 0 else "未知"
            
            # 获取表格引用
            table = record.locator(".trade-item")
            
            # 提取股票信息 (登录后在第一行的 td.darker 中)
            # 结构: tr:nth-child(1) > td.darker 包含 "江苏雷利(300660)"
            stock_name_el = table.locator("tr:nth-child(1) td.darker")
            stock_code = ""
            if stock_name_el.count() > 0:
                stock_code = stock_name_el.inner_text().strip()
            else:
                # 未登录时从 .trade-info-lock 获取
                stock_info_el = record.locator(".trade-info-lock p").first
                if stock_info_el.count() > 0:
                    stock_code = stock_info_el.inner_text().strip()
            
            # 提取仓位变化 (登录后在第二行的 td.darker 中)
            # 结构: tr:nth-child(2) > td.darker 包含 "个股仓位：13.94% → 29.95%"
            position_el = table.locator("tr:nth-child(2) td.darker")
            position_change = ""
            if position_el.count() > 0:
                position_text = position_el.inner_text().strip()
                # 提取 "个股仓位：xx% → xx%" 后面的部分
                if "：" in position_text:
                    position_change = position_text.split("：", 1)[1].strip()
                else:
                    position_change = position_text
            
            # 提取调仓时间 (在第一行的 td.weaker 中)
            # 结构: tr:nth-child(1) > td.weaker 包含 "调仓时间：02/03  09:52"
            time_el = table.locator("tr:nth-child(1) td.weaker")
            trade_time = ""
            if time_el.count() > 0:
                time_text = time_el.inner_text().strip()
                if "：" in time_text:
                    trade_time = time_text.split("：", 1)[1].strip()
                else:
                    trade_time = time_text
            
            # 提取价格 (在第二行的 td.weaker 中，登录后可见)
            # 结构: tr:nth-child(2) > td.weaker 包含 "价格：52.28元"
            price = ""
            price_el = table.locator("tr:nth-child(2) td.weaker")
            if price_el.count() > 0:
                price_text = price_el.inner_text().strip()
                if "：" in price_text:
                    price = price_text.split("：", 1)[1].strip()
                else:
                    price = price_text
            
            # 提取操作理由 (在 .reason-info 中)
            reason_el = record.locator(".reason-info")
            reason = reason_el.inner_text().strip() if reason_el.count() > 0 else ""
            
            result = {
                "trade_type": trade_type,
                "stock_code": stock_code,
                "position_change": position_change,
                "trade_time": trade_time,
                "price": price,
                "reason": reason,
            }
            
            print(f"📄 提取到结构化数据: {result}")
            return result
            
        except Exception as e:
            print(f"❌ 抓取出错: {e}")
            return None
    
    def get_all_records(self, url: Optional[str] = None) -> List[str]:
        """
        获取页面所有调仓记录
        
        Returns:
            所有记录的文本列表
        """
        target_url = url or config.TARGET_URL
        records = []
        
        if not self._page:
            print("❌ 浏览器未启动")
            return records
        
        try:
            self._page.goto(target_url, wait_until="networkidle")
            self._page.wait_for_timeout(config.RENDER_WAIT)
            
            for selector in self.RECORD_SELECTORS:
                items = self._page.locator(selector)
                count = items.count()
                if count > 0:
                    print(f"📄 找到 {count} 条记录（选择器: {selector}）")
                    for i in range(count):
                        text = items.nth(i).inner_text().strip()
                        if text:
                            records.append(text)
                    break
            
            return records
            
        except Exception as e:
            print(f"❌ 抓取出错: {e}")
            return records
    
    def screenshot(self, path: str = "screenshot.png") -> None:
        """保存页面截图（用于调试）"""
        if self._page:
            self._page.screenshot(path=path)
            print(f"📸 截图已保存: {path}")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
