# 平安证券组合调仓监控 (sbPush)

一个自动化监控平安证券组合调仓记录的 Python 工具，支持多渠道消息推送。

## ✨ 功能特性

- 🔄 **自动监控**：定时检查页面变化，发现新调仓立即通知
- 📱 **多渠道推送**：支持 Server酱、Bark、PushPlus、钉钉等多种推送方式
- 🔌 **可扩展设计**：基于开闭原则，轻松添加新推送渠道
- 🌐 **动态渲染**：使用 Playwright 处理 JavaScript 动态渲染页面
- 🛡️ **反爬绕过**：模拟真实浏览器环境，绕过常见反爬机制

## 📁 项目结构

```
sbPush/
├── main.py              # 主入口文件
├── requirements.txt     # Python 依赖
├── config/
│   └── .env.example     # 配置模板
└── src/
    ├── __init__.py
    ├── config.py        # 配置管理
    ├── monitor.py       # 监控核心逻辑
    ├── notifier.py      # 多渠道消息推送
    └── scraper.py       # 网页抓取
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装 Python 包
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置推送渠道

复制配置模板：

```bash
cp config/.env.example config/.env
```

编辑 `config/.env`，启用并配置你需要的推送渠道：

```ini
# 监控配置
TARGET_URL=https://m.stock.pingan.com/invest/zuhe/tradeRecord.html?productNo=5149
CHECK_INTERVAL=300

# 启用 Server酱
NOTIFIER_SERVER_CHAN_ENABLED=true
NOTIFIER_SERVER_CHAN_PUSH_KEY=你的SendKey

# 启用 Bark（可同时启用多个渠道）
NOTIFIER_BARK_ENABLED=true
NOTIFIER_BARK_DEVICE_KEY=你的DeviceKey
```

### 3. 测试运行

```bash
# 查看所有可用推送渠道
python main.py channels

# 测试抓取功能
python main.py test

# 测试推送功能（会向所有已启用渠道发送测试消息）
python main.py push-test

# 调试模式（显示浏览器窗口）
python main.py debug
```

### 4. 启动监控

```bash
python main.py monitor
```

## 📖 命令说明

| 命令 | 说明 |
|------|------|
| `python main.py monitor` | 启动监控服务 |
| `python main.py test` | 测试抓取功能 |
| `python main.py test -s` | 测试抓取并保存截图 |
| `python main.py push-test` | 测试所有已启用的推送渠道 |
| `python main.py channels` | 列出所有可用推送渠道 |
| `python main.py debug` | 调试模式（显示浏览器窗口） |

## 📢 支持的推送渠道

| 渠道 | 说明 | 配置项 |
|------|------|--------|
| `server_chan` | [Server酱](https://sct.ftqq.com) 微信推送 | `PUSH_KEY` |
| `bark` | [Bark](https://github.com/Finb/Bark) iOS 推送，**支持多用户** | `DEVICE_KEY`(逗号分隔), `SERVER`(可选) |
| `pushplus` | [PushPlus](https://www.pushplus.plus) 微信/企业微信 | `TOKEN` |
| `dingtalk` | 钉钉机器人 | `WEBHOOK` |

可以同时启用多个渠道，消息会推送到所有已启用的渠道。

### Bark 多用户配置示例

Bark 支持同时推送给多个用户，只需用英文逗号分隔多个 `device_key`：

```ini
NOTIFIER_BARK_ENABLED=true
NOTIFIER_BARK_DEVICE_KEY=key1,key2,key3
```

## 🔌 添加新推送渠道

项目采用 **开闭原则** 设计，添加新推送渠道只需 3 步，**无需修改现有代码**：

### 步骤 1：实现推送器类

在 `src/notifier.py` 中添加新的推送器类：

```python
@NotifierRegistry.register("your_channel")  # 注册渠道名称
class YourChannelNotifier(BaseNotifier):
    """
    你的推送渠道名称
    官网: https://example.com
    """
    
    def validate_config(self) -> bool:
        """验证必要配置是否存在"""
        return bool(self.config.get("api_key"))
    
    def send(self, title: str, content: str = "") -> NotifyResult:
        """
        发送推送
        
        Args:
            title: 推送标题
            content: 推送内容（Markdown 格式）
        
        Returns:
            NotifyResult: 推送结果
        """
        api_key = self.config.get("api_key")
        
        if not api_key:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message="未配置 api_key"
            )
        
        try:
            # 实现你的推送逻辑
            response = requests.post(
                "https://api.example.com/push",
                json={"title": title, "body": content, "key": api_key},
                timeout=10
            )
            result = response.json()
            
            if result.get("success"):
                return NotifyResult(
                    success=True,
                    channel=self.channel_name,
                    message="推送成功"
                )
            else:
                return NotifyResult(
                    success=False,
                    channel=self.channel_name,
                    message=result.get("error", "未知错误")
                )
                
        except Exception as e:
            return NotifyResult(
                success=False,
                channel=self.channel_name,
                message=f"推送异常: {e}"
            )
```

### 步骤 2：添加配置读取

在 `src/config.py` 的 `get_notifier_config()` 方法中添加配置映射：

```python
# 你的推送渠道配置
notifiers["your_channel"] = {
    "enabled": _get_bool("NOTIFIER_YOUR_CHANNEL_ENABLED"),
    "api_key": os.getenv("NOTIFIER_YOUR_CHANNEL_API_KEY", ""),
    # 添加其他需要的配置项...
}
```

### 步骤 3：更新配置模板

在 `config/.env.example` 中添加配置示例：

```ini
# --- 你的推送渠道 ---
# 官网: https://example.com
NOTIFIER_YOUR_CHANNEL_ENABLED=false
NOTIFIER_YOUR_CHANNEL_API_KEY=your_api_key
```

完成！新渠道会自动出现在 `python main.py channels` 列表中。

## 🔧 自定义选择器

如果抓取失败，需要手动调整页面选择器：

1. 在 Chrome 中打开目标页面
2. 按 `F12` 打开开发者工具
3. 点击左上角箭头图标，点击调仓记录元素
4. 查看元素的 CSS 类名
5. 修改 `src/scraper.py` 中的 `RECORD_SELECTORS`：

```python
RECORD_SELECTORS = [
    ".your-actual-class-name",  # 添加实际的类名
    # ...
]
```

## 🖥️ 部署方式

### 本地运行

```bash
# macOS/Linux 后台运行
nohup python main.py monitor > monitor.log 2>&1 &

# 查看日志
tail -f monitor.log
```

### 服务器部署

使用 systemd（Linux）：

```ini
# /etc/systemd/system/sbpush.service
[Unit]
Description=Stock Push Monitor
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/sbPush
ExecStart=/path/to/venv/bin/python main.py monitor
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable sbpush
sudo systemctl start sbpush
```

### Docker 部署（推荐）

1. **构建并启动容器**：

   ```bash
   docker-compose up -d --build
   ```

2. **常用管理命令**：

   ```bash
   # 查看日志
   docker-compose logs -f
   
   # 重启服务（修改配置后）
   docker-compose restart
   
   # 停止服务
   docker-compose down
   ```

3. **配置挂载**：
   容器会自动挂载本地的 `config/` 目录，所以你可以直接在主机上修改 `config/.env` 和 `config/cookies.json`，重启容器即可生效。

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────┐
│               NotifierManager                    │
│  (统一管理所有推送渠道，支持同时推送多渠道)        │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
┌────────┐  ┌────────┐   ┌──────────┐  ┌───────────┐
│Server酱│  │  Bark  │   │ PushPlus │  │  钉钉机器人│
└────────┘  └────────┘   └──────────┘  └───────────┘
    │             │             │              │
    └─────────────┴─────────────┴──────────────┘
                        │
              ┌─────────▼─────────┐
              │   BaseNotifier    │  (抽象基类)
              └───────────────────┘
```

- **BaseNotifier**：抽象基类，定义推送器接口
- **NotifierRegistry**：推送器注册表，使用装饰器自动注册
- **NotifierManager**：推送管理器，统一管理多渠道推送

## ⚠️ 注意事项

1. **检查间隔**：建议不低于 5 分钟（300秒），避免请求过于频繁
2. **反爬机制**：如遇验证码，可能需要添加 Cookie 或使用 stealth 插件
3. **选择器更新**：平安证券页面结构可能变化，需要定期检查选择器是否有效

## 📄 License

MIT License
