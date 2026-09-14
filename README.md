# 导师小帮手

Telegram 桌面工具：上分（通讯录备注金额）、展示页生成，以及私聊阅后即焚发图。电脑官方客户端不能发阅后即焚，本工具用你自己的账号通过官方 MTProto API 发送。

## 下载（推荐）

从 [Releases](https://github.com/suzheng5/telegram-view-once/releases) 下载 `TelegramViewOnce_4.zip`，解压后双击 `TelegramViewOnce_4.exe`。无需安装 Python。

请保持整个文件夹完整，不要只拷贝单个 exe。

## 功能

- **上分**：从 Telegram 通讯录备注读取「名字 UID 金额」，一键增加并写回备注；打开/关闭时自动备份到 `data/contacts_backup/`
- **展示**：生成资金追踪、防火墙等页面，点「复制-xxx」截成图并带到发图页
- **发图**：私聊发送阅后即焚图片（支持粘贴）

## 使用前准备

1. 打开 https://my.telegram.org/apps ，用你的手机号登录（不是机器人 Token）
2. 创建一个应用，记下 `api_id` 和 `api_hash`

首次启动会要求填写 `api_id` / `api_hash`，然后用手机 Telegram 扫描二维码登录（也支持手机号验证码）。支持多账号切换。

阅后即焚仅适用于**私聊**，群组和频道不支持。

会话文件保存在 `sessions/` 目录，等同于登录状态，请妥善保管，不要发给别人。

## 从源码运行

需要 [Python 3.10+](https://www.python.org/downloads/)。双击 `run.bat`，或：

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```
