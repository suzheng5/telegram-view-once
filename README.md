# Telegram 阅后即焚发送工具

电脑版 Telegram 不能发送阅后即焚（View Once）图片，本工具通过官方 MTProto API 补上这个功能。

## 下载（推荐）

从 [Releases](https://github.com/suzheng6/telegram-view-once/releases) 下载 `TelegramViewOnce_1.zip`，解压后双击 `TelegramViewOnce_1.exe`。无需安装 Python。

请保持整个文件夹完整，不要只拷贝单个 exe。

## 使用前准备

1. 打开 https://my.telegram.org/apps ，用你的手机号登录（不是机器人 Token）
2. 创建一个应用，记下 `api_id` 和 `api_hash`

首次启动会要求填写 `api_id` / `api_hash`，然后用手机 Telegram 扫描二维码登录（也支持手机号验证码）。登录成功后会读取私聊列表，选择联系人和图片即可发送阅后即焚照片。也可按 Ctrl+V 粘贴截图。支持多账号切换。

阅后即焚仅适用于**私聊**，群组和频道不支持。

会话文件保存在 `sessions/` 目录，等同于登录状态，请妥善保管，不要发给别人。

## 从源码运行

需要 [Python 3.10+](https://www.python.org/downloads/)。双击 `run.bat`，或：

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```
