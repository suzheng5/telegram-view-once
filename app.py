"""
导师小帮手 — 上分 + 阅后即焚（PySide6 Model/View）
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    import qrcode
    from PIL import Image, ImageGrab
    from PySide6.QtCore import (
        QAbstractListModel,
        QModelIndex,
        QPoint,
        QRect,
        QSize,
        Qt,
        QTimer,
        Signal,
        QObject,
    )
    from PySide6.QtGui import (
        QColor,
        QFont,
        QGuiApplication,
        QIcon,
        QImage,
        QKeySequence,
        QPainter,
        QPainterPath,
        QPixmap,
        QShortcut,
    )
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListView,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QStyle,
        QTabWidget,
        QStyledItemDelegate,
        QStyleOptionViewItem,
        QVBoxLayout,
        QWidget,
    )
    from telethon import errors
except ImportError:
    print("缺少依赖，请双击 run.bat 或执行：python -m pip install -r requirements.txt")
    sys.exit(1)

from services.contact_backup import ContactBackup
from services.contact_name import format_contact_name
from services.score import ScoreStore, local_now, money, next_amount
from tg_service import (
    APP_DIR,
    IMAGE_EXTS,
    LEGACY_SESSION,
    SESSIONS_DIR,
    AsyncRunner,
    TelegramService,
    load_config,
    save_config,
)
from ui.nullshield_page import NullShieldPage
from ui.score_page import ScorePage

APP_NAME = "导师小帮手"
APP_VERSION = "v1.4"
SEND_TAB = 2

BG = "#12151c"
PANEL = "#1b2030"
INPUT = "#222838"
HOVER = "#263044"
SELECTED = "#1e3a4d"
ACCENT = "#5ec8f0"
TEXT = "#f4f7fb"
TEXT_DIM = "#8b9bb0"
SUCCESS = "#34d399"
DANGER = "#fb7185"
BORDER = "#2d3a52"

IdRole = Qt.ItemDataRole.UserRole
NameRole = Qt.ItemDataRole.UserRole + 1
PreviewRole = Qt.ItemDataRole.UserRole + 2
TimeRole = Qt.ItemDataRole.UserRole + 3
AvatarRole = Qt.ItemDataRole.UserRole + 4
ChatRole = Qt.ItemDataRole.UserRole + 5

QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}}
QFrame#card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#topbar {{
    background: {PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLineEdit {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #0c1218;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {HOVER}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; }}
QPushButton#primary {{
    background: {ACCENT};
    color: #0c1218;
    border: none;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: #7ad4f4; }}
QPushButton#primary:disabled {{
    background: {INPUT};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    font-weight: 600;
}}
QComboBox {{
    background: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    min-width: 160px;
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid {BORDER};
    selection-background-color: {SELECTED};
    color: {TEXT};
}}
QListView {{
    background: transparent;
    border: none;
    outline: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#hint {{ color: {TEXT_DIM}; }}
QLabel#title {{ font-size: 18px; font-weight: 700; color: {ACCENT}; }}
QLabel#h {{ font-size: 14px; font-weight: 700; }}
QLabel#ok {{ color: {SUCCESS}; }}
QLabel#err {{ color: {DANGER}; }}
QLabel#badge {{
    background: #0c1218;
    color: {ACCENT};
    border-radius: 6px;
    padding: 2px 8px;
}}
QTabWidget#mainTabs::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: {INPUT};
    color: {TEXT_DIM};
    padding: 8px 22px;
    margin-right: 4px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    color: {ACCENT};
    font-weight: 700;
}}
QTableView {{
    background: transparent;
    border: none;
    outline: none;
    gridline-color: {BORDER};
    selection-background-color: {SELECTED};
    alternate-background-color: #161a24;
    color: {TEXT};
}}
QHeaderView::section {{
    background: {PANEL};
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 6px;
    font-weight: 600;
}}
QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
    color: {ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {ACCENT};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


def _window_icon() -> QIcon | None:
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", APP_DIR))
        candidates.extend([meipass / "icon.ico", APP_DIR / "icon.ico", Path(sys.executable)])
    else:
        candidates.append(Path(__file__).resolve().parent / "icon.ico")
    for path in candidates:
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return None


class UiBus(QObject):
    run = Signal(object)


class ChatListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._all: list[dict[str, Any]] = []
        self._rows: list[dict[str, Any]] = []
        self._avatars: dict[int, QPixmap] = {}
        self._keyword = ""

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        chat = self._rows[index.row()]
        uid = int(chat["id"])
        if role == Qt.DisplayRole or role == NameRole:
            return chat["name"]
        if role == IdRole:
            return uid
        if role == PreviewRole:
            if chat.get("preview"):
                return chat["preview"]
            if chat.get("username"):
                return "@" + chat["username"]
            return "私聊"
        if role == TimeRole:
            return chat.get("time") or ""
        if role == AvatarRole:
            return self._avatars.get(uid)
        if role == ChatRole:
            return chat
        return None

    def set_chats(self, chats: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._all = chats
        self._avatars.clear()
        self._apply()
        self.endResetModel()

    def set_keyword(self, keyword: str) -> None:
        self.beginResetModel()
        self._keyword = keyword.strip().lower()
        self._apply()
        self.endResetModel()

    def _apply(self) -> None:
        kw = self._keyword
        if not kw:
            self._rows = list(self._all)
            return
        self._rows = [
            c
            for c in self._all
            if kw in c["name"].lower()
            or kw in (c.get("username") or "").lower()
            or kw in (c.get("phone") or "")
        ]

    def chat_at(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def set_avatar(self, uid: int, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data):
            return
        pix = pix.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._avatars[uid] = pix
        for i, chat in enumerate(self._rows):
            if int(chat["id"]) == uid:
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [AvatarRole])
                break


class ChatDelegate(QStyledItemDelegate):
    ROW_H = 60

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect.adjusted(6, 3, -6, -3)
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        if selected:
            painter.fillPath(path, QColor(SELECTED))
            bar = QRect(rect.left(), rect.top() + 8, 3, rect.height() - 16)
            painter.fillRect(bar, QColor(ACCENT))
        elif hover:
            painter.fillPath(path, QColor(HOVER))

        name = index.data(NameRole) or ""
        preview = index.data(PreviewRole) or ""
        time_text = index.data(TimeRole) or ""
        avatar: QPixmap | None = index.data(AvatarRole)

        ax, ay, asize = rect.left() + 12, rect.top() + 10, 40
        clip = QPainterPath()
        clip.addEllipse(ax, ay, asize, asize)
        painter.setClipPath(clip)
        if avatar and not avatar.isNull():
            painter.drawPixmap(ax, ay, asize, asize, avatar)
        else:
            painter.fillPath(clip, QColor("#3d5a80"))
            painter.setClipping(False)
            painter.setPen(QColor(TEXT))
            painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
            painter.drawText(QRect(ax, ay, asize, asize), Qt.AlignCenter, (name[:1] or "?").upper())
        painter.setClipping(False)

        painter.setPen(QColor(TEXT))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.DemiBold))
        painter.drawText(ax + asize + 10, rect.top() + 22, name)
        painter.setPen(QColor(TEXT_DIM))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(ax + asize + 10, rect.top() + 42, preview[:32])
        painter.drawText(
            rect.adjusted(0, 8, -12, 0), Qt.AlignRight | Qt.AlignTop, time_text
        )
        painter.restore()


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)
        icon = _window_icon()
        if icon:
            self.setWindowIcon(icon)
        self.setStyleSheet(QSS)

        self.runner = AsyncRunner()
        self.service = TelegramService()
        self.bus = UiBus()
        self.bus.run.connect(self._ui, Qt.QueuedConnection)

        self.config_data = load_config()
        self.selected: dict[str, Any] | None = None
        self.image_path: Path | None = None
        self._preview_pix: QPixmap | None = None
        self._phone = ""
        self._busy = False
        self._need_2fa = False
        self._login_busy = False
        self._avatar_done: set[int] = set()
        self._avatar_inflight: set[int] = set()
        self._avatar_bytes: dict[int, bytes] = {}
        self._switch_back_id: int | None = None
        self.score_store = ScoreStore(APP_DIR)
        self.contact_backup = ContactBackup(APP_DIR)

        self.model = ChatListModel()
        self._build()
        QShortcut(QKeySequence.Paste, self, activated=self._on_paste_shortcut)
        QTimer.singleShot(80, self._boot)

    def _ui(self, fn) -> None:
        fn()

    def call(self, fn) -> None:
        self.bus.run.emit(fn)

    def _thread(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _accounts(self) -> list[dict[str, Any]]:
        return list(self.config_data.get("accounts") or [])

    def _account_label(self, acc: dict[str, Any]) -> str:
        text = acc.get("name") or str(acc.get("id"))
        if acc.get("username"):
            text += f"  {acc['username']}"
        return text

    def _save(self) -> None:
        save_config(self.config_data)

    def _register_account(self, me: dict[str, Any], session_path: str) -> None:
        acc = {
            "id": int(me["id"]),
            "name": me["name"],
            "username": me.get("username") or "",
            "session": session_path,
        }
        accounts = [a for a in self._accounts() if int(a["id"]) != int(me["id"])]
        accounts.append(acc)
        self.config_data["accounts"] = accounts
        self.config_data["active_id"] = int(me["id"])
        self._save()

    def _remove_account(self, user_id: int) -> None:
        accounts = [a for a in self._accounts() if int(a["id"]) != int(user_id)]
        self.config_data["accounts"] = accounts
        if self.config_data.get("active_id") == user_id:
            self.config_data["active_id"] = accounts[0]["id"] if accounts else None
        self._save()

    def _new_pending_session(self) -> str:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return str(SESSIONS_DIR / f"pending_{int(time.time())}")

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_setup())
        self.stack.addWidget(self._page_login())
        self.stack.addWidget(self._page_main())
        root.addWidget(self.stack)

    def _card(self) -> QFrame:
        box = QFrame()
        box.setObjectName("card")
        return box

    def _btn(self, text: str, handler, primary=False) -> QPushButton:
        btn = QPushButton(text)
        if primary:
            btn.setObjectName("primary")
        btn.clicked.connect(handler)
        return btn

    def _page_setup(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 36)
        card = self._card()
        inner = QVBoxLayout(card)
        inner.setContentsMargins(28, 28, 28, 28)
        inner.setSpacing(8)
        title = QLabel("连接 Telegram API")
        title.setObjectName("title")
        inner.addWidget(title)
        hint = QLabel(
            "用你自己的 Telegram 账号登录：上分改通讯录备注，发图走阅后即焚。\n"
            "1. 浏览器打开  https://my.telegram.org/apps\n"
            "2. 用本机 Telegram 手机号登录（不是机器人 Token）\n"
            "3. 创建一个应用，把 api_id 和 api_hash 填到下面"
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        inner.addWidget(hint)
        inner.addWidget(QLabel("api_id"))
        self.api_id_edit = QLineEdit()
        inner.addWidget(self.api_id_edit)
        inner.addWidget(QLabel("api_hash"))
        self.api_hash_edit = QLineEdit()
        inner.addWidget(self.api_hash_edit)
        if self.config_data.get("api_id"):
            self.api_id_edit.setText(str(self.config_data["api_id"]))
        if self.config_data.get("api_hash"):
            self.api_hash_edit.setText(str(self.config_data["api_hash"]))
        inner.addWidget(self._btn("保存并继续", self._save_setup, primary=True))
        self.setup_status = QLabel("")
        self.setup_status.setWordWrap(True)
        inner.addWidget(self.setup_status)
        inner.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _page_login(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(20, 20, 20, 20)
        row.setSpacing(16)

        left = self._card()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(22, 22, 22, 22)
        t = QLabel("扫码登录")
        t.setObjectName("title")
        ll.addWidget(t)
        h = QLabel("打开手机 Telegram → 设置 → 设备 → 扫描二维码")
        h.setObjectName("hint")
        h.setWordWrap(True)
        ll.addWidget(h)
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(220, 220)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet("background:#ffffff; border-radius:8px;")
        ll.addWidget(self.qr_label, alignment=Qt.AlignLeft)
        self.qr_status = QLabel("正在生成二维码…")
        self.qr_status.setObjectName("hint")
        self.qr_status.setWordWrap(True)
        ll.addWidget(self.qr_status)
        ll.addStretch()

        right = self._card()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(22, 22, 22, 22)
        t2 = QLabel("手机号登录")
        t2.setObjectName("title")
        rl.addWidget(t2)
        h2 = QLabel("国际格式，例如 +8613800138000")
        h2.setObjectName("hint")
        rl.addWidget(h2)
        rl.addWidget(QLabel("手机号"))
        self.phone_edit = QLineEdit()
        rl.addWidget(self.phone_edit)
        rl.addWidget(self._btn("发送验证码", self._send_code))
        rl.addWidget(QLabel("短信 / App 验证码"))
        self.code_edit = QLineEdit()
        self.code_edit.returnPressed.connect(self._try_login)
        rl.addWidget(self.code_edit)
        rl.addWidget(self._btn("登录", self._try_login, primary=True))
        box = QFrame()
        box.setStyleSheet(f"background:{INPUT}; border-radius:8px;")
        bl = QVBoxLayout(box)
        tip = QLabel("两步验证密码（设置里自己设定的密码，不是上面的验证码）")
        tip.setWordWrap(True)
        bl.addWidget(tip)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self._sign_in_password)
        bl.addWidget(self.password_edit)
        bl.addWidget(self._btn("提交两步验证密码并登录", self._sign_in_password, primary=True))
        rl.addWidget(box)
        self.login_status = QLabel("")
        self.login_status.setWordWrap(True)
        rl.addWidget(self.login_status)
        self.login_back_btn = self._btn("返回已登录账号", self._back_to_accounts)
        self.login_back_btn.hide()
        rl.addWidget(self.login_back_btn)
        rl.addStretch()

        row.addWidget(left, 1)
        row.addWidget(right, 1)
        return page

    def _page_main(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        top = QFrame()
        top.setObjectName("topbar")
        top.setFixedHeight(56)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(18, 8, 18, 8)
        mark = QLabel("●")
        mark.setStyleSheet(f"color:{ACCENT}; font-size:18px;")
        title = QLabel(APP_NAME)
        title.setObjectName("h")
        self.conn_label = QLabel("已连接")
        self.conn_label.setObjectName("ok")
        self.account_combo = QComboBox()
        self.account_combo.currentIndexChanged.connect(self._on_account_combo)
        self.me_label = QLabel("")
        self.me_label.setObjectName("hint")
        tl.addWidget(mark)
        tl.addWidget(title)
        tl.addWidget(self.conn_label)
        tl.addWidget(self.account_combo)
        tl.addWidget(self.me_label, 1)
        tl.addWidget(self._btn("刷新", self._reload_chats))
        tl.addWidget(self._btn("添加账号", self._add_account))
        tl.addWidget(self._btn("退出当前账号", self._logout))
        col.addWidget(top)

        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(16)
        split = QSplitter(Qt.Horizontal)

        left = self._card()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        h = QLabel("私聊")
        h.setObjectName("h")
        ll.addWidget(h)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索联系人")
        self.search_edit.textChanged.connect(self._on_search)
        ll.addWidget(self.search_edit)
        self.chat_view = QListView()
        self.chat_view.setModel(self.model)
        self.chat_view.setItemDelegate(ChatDelegate())
        self.chat_view.setUniformItemSizes(True)
        self.chat_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.chat_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.chat_view.setMouseTracking(True)
        self.chat_view.clicked.connect(self._on_chat_clicked)
        self.chat_view.selectionModel().currentChanged.connect(
            lambda cur, _prev: self._on_chat_clicked(cur) if cur.isValid() else None
        )
        self.chat_view.verticalScrollBar().valueChanged.connect(self._schedule_avatars)
        ll.addWidget(self.chat_view, 1)

        right = self._card()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 18, 18, 18)
        rh = QLabel("发送阅后即焚")
        rh.setObjectName("h")
        rl.addWidget(rh)
        recv = QLabel("接收方")
        recv.setObjectName("hint")
        rl.addWidget(recv)
        self.target_label = QLabel("请在左侧选择一位联系人")
        self.target_label.setObjectName("hint")
        self.target_label.setWordWrap(True)
        rl.addWidget(self.target_label)

        preview_wrap = QFrame()
        preview_wrap.setStyleSheet(
            f"background:{INPUT}; border:1px solid {BORDER}; border-radius:12px;"
        )
        preview_wrap.setMinimumHeight(220)
        pl = QVBoxLayout(preview_wrap)
        self.preview = QLabel("选择或粘贴图片后在这里预览")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setObjectName("hint")
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pl.addWidget(self.preview)
        badge = QLabel("阅后即焚")
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignRight)
        pl.addWidget(badge, alignment=Qt.AlignRight)
        rl.addWidget(preview_wrap, 1)

        btns = QHBoxLayout()
        btns.addWidget(self._btn("选择图片", self._pick_image))
        btns.addWidget(self._btn("粘贴图片", self._paste_image))
        btns.addWidget(self._btn("清除", self._clear_image))
        btns.addStretch()
        rl.addLayout(btns)
        rl.addWidget(QLabel("说明文字（可选）"))
        self.caption_edit = QLineEdit()
        self.caption_edit.setPlaceholderText("说点什么…")
        rl.addWidget(self.caption_edit)
        self.send_btn = self._btn("发送阅后即焚", self._send, primary=True)
        rl.addWidget(self.send_btn)
        self.main_status = QLabel("对方查看一次后自毁")
        self.main_status.setObjectName("hint")
        self.main_status.setWordWrap(True)
        rl.addWidget(self.main_status)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 4)
        wrap = QWidget()
        wrap.setLayout(body)
        body.addWidget(split)

        self.score_page = ScorePage()
        self.score_page.increase_requested.connect(self._on_score_increase)
        self.score_page.need_avatars.connect(self._on_score_need_avatars)
        self.display_page = NullShieldPage()
        self.display_page.image_ready.connect(self._on_display_image)

        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("mainTabs")
        self.main_tabs.addTab(self.score_page, "上分")
        self.main_tabs.addTab(self.display_page, "展示")
        self.main_tabs.addTab(wrap, "发图")
        col.addWidget(self.main_tabs, 1)
        return page

    def _show(self, name: str) -> None:
        self.stack.setCurrentIndex({"setup": 0, "login": 1, "main": 2}[name])

    def _on_search(self, text: str) -> None:
        self.model.set_keyword(text)
        self._schedule_avatars()

    def _on_chat_clicked(self, index: QModelIndex) -> None:
        chat = self.model.chat_at(index.row())
        if not chat:
            return
        self.selected = chat
        extra = f"  @{chat['username']}" if chat.get("username") else ""
        self.target_label.setText(f"发送给：{chat['name']}{extra}")
        self.target_label.setStyleSheet(f"color:{TEXT};")

    def _rebuild_accounts(self) -> None:
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        active = self.config_data.get("active_id")
        current = 0
        for i, acc in enumerate(self._accounts()):
            self.account_combo.addItem(self._account_label(acc), int(acc["id"]))
            if int(acc["id"]) == active:
                current = i
        if self.account_combo.count():
            self.account_combo.setCurrentIndex(current)
        self.account_combo.blockSignals(False)

    def _on_account_combo(self, index: int) -> None:
        if index < 0:
            return
        uid = self.account_combo.itemData(index)
        if uid is None:
            return
        self._switch_account(int(uid))

    def _boot(self) -> None:
        api_id = self.config_data.get("api_id")
        api_hash = self.config_data.get("api_hash")
        if not api_id or not api_hash:
            self._show("setup")
            return
        accounts = self._accounts()
        active = self.config_data.get("active_id")
        if accounts:
            acc = next((a for a in accounts if int(a["id"]) == active), accounts[0])
            self._show("main")
            self._set_main_status("正在连接…", TEXT_DIM)
            self._connect(str(acc["session"]), False)
            return
        if Path(LEGACY_SESSION + ".session").exists():
            self._show("main")
            self._set_main_status("正在连接…", TEXT_DIM)
            self._connect(LEGACY_SESSION, False)
            return
        self._need_2fa = False
        self._show_login()
        self._connect(self._new_pending_session(), True)

    def _show_login(self) -> None:
        self._show("login")
        self.login_back_btn.setVisible(bool(self._accounts()))

    def _save_setup(self) -> None:
        api_id_raw = self.api_id_edit.text().strip()
        api_hash = self.api_hash_edit.text().strip()
        if not api_id_raw.isdigit() or not api_hash:
            self.setup_status.setText("请填写有效的 api_id（数字）和 api_hash")
            self.setup_status.setObjectName("err")
            self.setup_status.setStyleSheet(f"color:{DANGER};")
            return
        self.config_data["api_id"] = int(api_id_raw)
        self.config_data["api_hash"] = api_hash
        self._save()
        self._need_2fa = False
        self._show_login()
        self._set_login_status("正在连接 Telegram…", TEXT_DIM)
        self._connect(self._new_pending_session(), True)

    def _connect(self, session_path: str, expect_login: bool) -> None:
        api_id = int(self.config_data["api_id"])
        api_hash = str(self.config_data["api_hash"])
        self._set_login_status("正在连接 Telegram…", TEXT_DIM)

        def work():
            try:
                authorized = self.runner.submit(
                    self.service.connect(api_id, api_hash, session_path)
                ).result()
            except Exception as exc:
                self.call(lambda: self._set_login_status(f"连接失败：{exc}", DANGER))
                self.call(lambda: self._show("setup"))
                return
            if authorized:
                self.call(self._after_authorized)
            else:
                self.call(self._show_login)
                self.call(self._start_qr)

        self._thread(work)

    def _after_authorized(self) -> None:
        api_id = int(self.config_data["api_id"])
        api_hash = str(self.config_data["api_hash"])

        def work():
            try:
                me = self.runner.submit(self.service.me()).result()
                dest = self.runner.submit(
                    self.service.adopt_session(int(me["id"]), api_id, api_hash)
                ).result()
            except Exception as exc:
                self.call(lambda: self._set_login_status(f"保存登录状态失败：{exc}", DANGER))
                return
            self.call(lambda: self._finish_register(me, dest))

        self._thread(work)

    def _finish_register(self, me: dict[str, Any], session_path: str) -> None:
        self._register_account(me, session_path)
        self._need_2fa = False
        self._login_busy = False
        self._enter_main()

    def _reset_chat_list(self) -> None:
        self.selected = None
        self._avatar_done.clear()
        self._avatar_inflight.clear()
        self._avatar_bytes.clear()
        self.model.set_chats([])
        self.chat_view.clearSelection()
        self.target_label.setText("请在左侧选择一位联系人")
        self.target_label.setStyleSheet(f"color:{TEXT_DIM};")
        self.score_page.reset()

    def _enter_main(self) -> None:
        self.service.cancel_qr()
        self.login_back_btn.hide()
        self._show("main")
        self._reset_chat_list()
        self._set_main_status("正在加载聊天列表…", TEXT_DIM)

        def work():
            try:
                me = self.runner.submit(self.service.me()).result()
                chats = self.runner.submit(self.service.list_private_chats()).result()
                scores = self.runner.submit(self.service.list_score_contacts()).result()
            except Exception as exc:
                self.call(lambda: self._set_main_status(f"加载失败：{exc}", DANGER))
                return
            self.call(lambda: self._fill_main(me, chats, scores))

        self._thread(work)

    def _fill_main(
        self, me: dict[str, Any], chats: list[dict[str, Any]], scores: list[dict[str, Any]]
    ) -> None:
        who = me["name"] + (f"  {me['username']}" if me["username"] else "")
        self.me_label.setText(who)
        self._rebuild_accounts()
        self.selected = None
        self.target_label.setText("请在左侧选择一位联系人")
        self._avatar_done.clear()
        self._avatar_inflight.clear()
        self._avatar_bytes.clear()
        self.model.set_chats(chats)
        scores = TelegramService.sort_scores_like_chats(scores, chats)
        self.score_page.set_contacts(scores, self.score_store, int(me["id"]))
        self._apply_saved_avatars(int(me["id"]))
        saved = self._backup_contacts(int(me["id"]))
        self._set_main_status(f"已加载 {len(chats)} 个私聊，上分 {len(scores)} 人", SUCCESS)
        if saved:
            self.score_page.set_status(
                f"可上分 {len(scores)} 人，本地已备份 {saved} 人", SUCCESS
            )
        QTimer.singleShot(80, self._load_visible_avatars)

    def _schedule_avatars(self, *_args) -> None:
        QTimer.singleShot(60, self._load_visible_avatars)

    def _visible_ids(self) -> list[int]:
        view = self.chat_view
        first = view.indexAt(QPoint(8, 8))
        last = view.indexAt(QPoint(8, max(8, view.viewport().height() - 8)))
        start = first.row() if first.isValid() else 0
        end = last.row() if last.isValid() else min(20, self.model.rowCount() - 1)
        ids = []
        for row in range(max(0, start), min(self.model.rowCount(), end + 4)):
            chat = self.model.chat_at(row)
            if chat:
                ids.append(int(chat["id"]))
        return ids

    def _load_visible_avatars(self) -> None:
        needed = [
            uid
            for uid in self._visible_ids()
            if uid not in self._avatar_done and uid not in self._avatar_inflight
        ]
        if not needed:
            return
        for uid in needed:
            self._avatar_inflight.add(uid)

        def on_one(uid: int, data: bytes) -> None:
            self.call(lambda u=uid, d=data: self._set_avatar(u, d))

        def work(batch=list(needed)):
            try:
                self.runner.submit(self.service.fetch_avatars(batch, on_one)).result()
            except Exception:
                pass
            for uid in batch:
                self._avatar_inflight.discard(uid)
                self._avatar_done.add(uid)

        self._thread(work)

    def _set_avatar(self, uid: int, data: bytes) -> None:
        self._avatar_bytes[uid] = data
        self.model.set_avatar(uid, data)
        self.score_page.set_avatar(uid, data)
        self._avatar_done.add(uid)
        account_id = self._active_account_id()
        if account_id:
            try:
                self.contact_backup.save_avatar(account_id, uid, data)
            except OSError:
                pass

    def _active_account_id(self) -> int | None:
        if getattr(self, "score_page", None) is not None and self.score_page.account_id:
            return int(self.score_page.account_id)
        raw = self.config_data.get("active_id")
        return int(raw) if raw else None

    def _apply_saved_avatars(self, account_id: int) -> None:
        try:
            blobs = self.contact_backup.load_avatars(account_id)
        except OSError:
            return
        for uid, data in blobs.items():
            self._avatar_bytes.setdefault(uid, data)
            self.model.set_avatar(uid, data)
            self.score_page.set_avatar(uid, data)

    def _backup_contacts(self, account_id: int | None = None) -> int:
        aid = account_id or self._active_account_id()
        if not aid or not getattr(self, "score_page", None):
            return 0
        try:
            return self.contact_backup.save(aid, self.score_page.backup_rows())
        except OSError:
            return 0

    def _on_score_need_avatars(self, ids: list[int]) -> None:
        for uid in ids:
            cached = self._avatar_bytes.get(uid)
            if cached:
                self.score_page.set_avatar(uid, cached)
        needed = [
            uid
            for uid in ids
            if uid not in self._avatar_done and uid not in self._avatar_inflight
        ]
        if not needed:
            return
        for uid in needed:
            self._avatar_inflight.add(uid)

        def on_one(uid: int, data: bytes) -> None:
            self.call(lambda u=uid, d=data: self._set_avatar(u, d))

        def work(batch=list(needed)):
            try:
                self.runner.submit(self.service.fetch_avatars(batch, on_one)).result()
            except Exception:
                pass
            for uid in batch:
                self._avatar_inflight.discard(uid)
                self._avatar_done.add(uid)

        self._thread(work)

    def _on_score_increase(self, items: Any) -> None:
        queue = list(items) if isinstance(items, (list, tuple)) else [items]

        def work():
            done: list[tuple[Any, Any, str, str, str, str]] = []
            failed: list[tuple[Any, str]] = []
            skipped = False
            for item in queue:
                if skipped:
                    failed.append((item, "已跳过（频率限制）"))
                    continue
                try:
                    bump, new_amount = next_amount(
                        item.amount_decimal, item.rate_decimal
                    )
                    new_name = format_contact_name(
                        item.name, item.uid, new_amount, item.rate_decimal
                    )
                    self.runner.submit(
                        self.service.update_contact_name(item.user_id, new_name)
                    ).result()
                except errors.FloodWaitError as exc:
                    failed.append((item, f"操作太频繁，需等待 {exc.seconds} 秒"))
                    skipped = True
                    continue
                except Exception as exc:
                    failed.append((item, str(exc)))
                    continue
                when = local_now().isoformat(timespec="seconds")
                done.append(
                    (item, new_amount, when, money(bump), money(new_amount), new_name)
                )
            self.call(lambda: self._after_score_increases(done, failed))

        self._thread(work)

    def _after_score_increases(
        self,
        done: list[tuple[Any, Any, str, str, str, str]],
        failed: list[tuple[Any, str]],
    ) -> None:
        copied = []
        for item, new_amount, when, _bump, _current, raw_name in done:
            self.score_page.apply_increase(item.user_id, new_amount, when, raw_name)
            copied.append((item.uid, new_amount))
        for item, _reason in failed:
            self.score_page.release_busy(item.user_id)

        if copied:
            self.score_page.copy_uid_amounts(copied)

        ok = len(done)
        bad = len(failed)
        if ok == 1 and bad == 0:
            item, _amount, _when, increase_text, current_text, _name = done[0]
            self.score_page.set_status(
                f"{item.name} 已增加 {increase_text}，当前 {current_text}，已复制",
                SUCCESS,
            )
            return
        if ok and bad == 0:
            self.score_page.set_status(f"已增加 {ok} 人，已复制 {ok} 行", SUCCESS)
            return
        if ok and bad:
            reason = failed[0][1]
            self.score_page.set_status(
                f"已增加 {ok} 人并复制，失败 {bad} 人：{reason}", DANGER
            )
            return
        if bad == 1:
            item, reason = failed[0]
            self.score_page.set_status(f"{item.name} 上分失败：{reason}", DANGER)
            return
        if bad:
            self.score_page.set_status(f"上分失败 {bad} 人：{failed[0][1]}", DANGER)

    def _start_qr(self) -> None:
        self._set_qr_status("请用手机 Telegram 扫描二维码", TEXT_DIM)

        def on_url(url: str) -> None:
            self.call(lambda: self._show_qr(url))

        def work():
            try:
                self.runner.submit(
                    self.service.qr_login(
                        on_url, [int(a["id"]) for a in self._accounts()]
                    )
                ).result()
            except asyncio.CancelledError:
                return
            except errors.SessionPasswordNeededError:
                self.call(
                    lambda: self._on_2fa_needed(
                        "扫码成功，请输入两步验证密码后点「提交两步验证密码并登录」"
                    )
                )
                return
            except Exception as exc:
                self.call(lambda: self._set_qr_status(f"扫码登录失败：{exc}", DANGER))
                return
            self.call(self._after_authorized)

        self._thread(work)

    def _show_qr(self, url: str) -> None:
        qr = qrcode.QRCode(border=2, box_size=6)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buf = img.tobytes("raw", "RGB")
        qimg = QImage(buf, img.size[0], img.size[1], QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg).scaled(200, 200, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.qr_label.setPixmap(pix)
        self._set_qr_status("二维码会自动刷新，请尽快扫描", TEXT_DIM)

    def _send_code(self) -> None:
        phone = self.phone_edit.text().strip().replace(" ", "")
        if not phone.startswith("+") or len(phone) < 8:
            self._set_login_status("请填写国际格式手机号，例如 +86…", DANGER)
            return
        self._phone = phone
        self._need_2fa = False
        self.service.cancel_qr()
        self._set_login_status("正在发送验证码…", TEXT_DIM)

        def work():
            try:
                self.runner.submit(self.service.send_code(phone)).result()
            except errors.FloodWaitError as exc:
                self.call(
                    lambda: self._set_login_status(
                        f"操作过于频繁，请等待 {exc.seconds} 秒", DANGER
                    )
                )
                return
            except Exception as exc:
                self.call(lambda: self._set_login_status(f"发送失败：{exc}", DANGER))
                return
            self.call(lambda: self._set_login_status("验证码已发送，请查看 Telegram 后点登录", SUCCESS))

        self._thread(work)

    def _try_login(self) -> None:
        if self._need_2fa:
            self._sign_in_password()
        else:
            self._sign_in_code()

    def _on_2fa_needed(self, message: str) -> None:
        self._need_2fa = True
        self._set_login_status(message, ACCENT)
        self.password_edit.setFocus()
        if self.password_edit.text():
            self._sign_in_password()

    def _sign_in_code(self) -> None:
        code = self.code_edit.text().strip()
        phone = self._phone or self.phone_edit.text().strip()
        if not phone or not code:
            self._set_login_status("请先获取验证码，再填写验证码后点登录", DANGER)
            return
        self._set_login_status("正在验证…", TEXT_DIM)

        def work():
            try:
                self.runner.submit(self.service.sign_in_code(phone, code)).result()
            except errors.SessionPasswordNeededError:
                self.call(
                    lambda: self._on_2fa_needed(
                        "验证码正确。请填写两步验证密码（不是短信验证码），然后点「提交两步验证密码并登录」"
                    )
                )
                return
            except errors.PhoneCodeInvalidError:
                self.call(lambda: self._set_login_status("验证码不正确", DANGER))
                return
            except errors.PhoneCodeExpiredError:
                self.call(lambda: self._set_login_status("验证码已过期，请重新发送", DANGER))
                return
            except Exception as exc:
                self.call(lambda: self._set_login_status(f"登录失败：{exc}", DANGER))
                return
            self.call(self._after_authorized)

        self._thread(work)

    def _sign_in_password(self) -> None:
        if self._login_busy:
            return
        password = self.password_edit.text()
        if not password:
            self._set_login_status("请输入两步验证密码（不是短信验证码）", DANGER)
            self.password_edit.setFocus()
            return
        self._login_busy = True
        self._set_login_status("正在提交两步验证密码…", TEXT_DIM)

        def work():
            try:
                self.runner.submit(self.service.sign_in_password(password)).result()
            except errors.PasswordHashInvalidError:
                self.call(self._unlock_login)
                self.call(
                    lambda: self._set_login_status(
                        "两步验证密码不正确。这是 Telegram「隐私与安全 → 两步验证」里的密码。",
                        DANGER,
                    )
                )
                return
            except Exception as exc:
                self.call(self._unlock_login)
                self.call(lambda: self._set_login_status(f"登录失败：{exc}", DANGER))
                return
            self.call(self._after_authorized)

        self._thread(work)

    def _unlock_login(self) -> None:
        self._login_busy = False

    def _set_login_status(self, text: str, color: str) -> None:
        self.login_status.setText(text)
        self.login_status.setStyleSheet(f"color:{color};")
        self.qr_status.setText(text)
        self.qr_status.setStyleSheet(f"color:{color};")

    def _set_qr_status(self, text: str, color: str) -> None:
        self.qr_status.setText(text)
        self.qr_status.setStyleSheet(f"color:{color};")

    def _set_main_status(self, text: str, color: str = TEXT_DIM) -> None:
        self.main_status.setText(text)
        self.main_status.setStyleSheet(f"color:{color};")

    def _reload_chats(self) -> None:
        self._set_main_status("正在刷新…", TEXT_DIM)

        def work():
            try:
                chats = self.runner.submit(self.service.list_private_chats()).result()
                scores = self.runner.submit(self.service.list_score_contacts()).result()
            except Exception as exc:
                self.call(lambda: self._set_main_status(f"刷新失败：{exc}", DANGER))
                return
            self.call(lambda: self._after_reload(chats, scores))

        self._thread(work)

    def _after_reload(
        self, chats: list[dict[str, Any]], scores: list[dict[str, Any]]
    ) -> None:
        self.model.set_chats(chats)
        self._avatar_done.clear()
        self._avatar_inflight.clear()
        self._avatar_bytes.clear()
        scores = TelegramService.sort_scores_like_chats(scores, chats)
        account_id = int(self.config_data.get("active_id") or 0)
        if account_id:
            self.score_page.set_contacts(scores, self.score_store, account_id)
            self._apply_saved_avatars(account_id)
            saved = self._backup_contacts(account_id)
            if saved:
                self.score_page.set_status(
                    f"可上分 {len(scores)} 人，本地已备份 {saved} 人", SUCCESS
                )
        self._set_main_status(
            f"已刷新，私聊 {len(chats)}，上分 {len(scores)} 人", SUCCESS
        )
        self._schedule_avatars()

    def _add_account(self) -> None:
        self._backup_contacts()
        self._switch_back_id = self.config_data.get("active_id")
        self._need_2fa = False
        self._login_busy = False
        self.selected = None

        def work():
            try:
                self.runner.submit(self.service.disconnect()).result()
            except Exception:
                pass
            self.call(self._show_login)
            self.call(lambda: self._set_login_status("请登录要添加的新账号", TEXT))
            self.call(lambda: self._connect(self._new_pending_session(), True))

        self._thread(work)

    def _switch_account(self, user_id: int) -> None:
        if int(user_id) == self.config_data.get("active_id") and self.stack.currentIndex() == 2:
            return
        acc = next((a for a in self._accounts() if int(a["id"]) == int(user_id)), None)
        if not acc:
            return
        self._backup_contacts()
        self._reset_chat_list()
        self._clear_image()
        self.me_label.setText(self._account_label(acc))
        self.config_data["active_id"] = int(user_id)
        self._save()
        self._set_main_status("正在切换账号…", TEXT_DIM)

        def work():
            try:
                self.runner.submit(self.service.disconnect()).result()
            except Exception:
                pass
            self.call(lambda: self._connect(str(acc["session"]), False))

        self._thread(work)

    def _back_to_accounts(self) -> None:
        self.service.cancel_qr()
        accounts = self._accounts()
        if not accounts:
            return
        target = self._switch_back_id or self.config_data.get("active_id")
        if target is None or not any(int(a["id"]) == int(target) for a in accounts):
            target = accounts[0]["id"]
        self._switch_account(int(target))

    def _on_paste_shortcut(self) -> None:
        w = QApplication.focusWidget()
        if isinstance(w, QLineEdit):
            return
        if self.stack.currentIndex() != 2 or self.main_tabs.currentIndex() != SEND_TAB:
            return
        self._paste_image()

    def _paste_image(self) -> None:
        if self.stack.currentIndex() != 2 or self.main_tabs.currentIndex() != SEND_TAB:
            return
        clip = QGuiApplication.clipboard()
        qimg = clip.image()
        if not qimg.isNull():
            dest = APP_DIR / "_clipboard.jpg"
            qimg.save(str(dest), "JPG", 95)
            self._load_image_path(dest)
            return
        mime = clip.mimeData()
        if mime and mime.hasUrls():
            files = [
                Path(u.toLocalFile())
                for u in mime.urls()
                if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in IMAGE_EXTS
            ]
            if files:
                self._load_image_path(files[0])
                return
        try:
            grabbed = ImageGrab.grabclipboard()
        except Exception as exc:
            self._set_main_status(f"读取剪贴板失败：{exc}", DANGER)
            return
        if isinstance(grabbed, Image.Image):
            dest = APP_DIR / "_clipboard.jpg"
            grabbed.convert("RGB").save(dest, "JPEG", quality=95)
            self._load_image_path(dest)
            return
        if isinstance(grabbed, list):
            files = [Path(p) for p in grabbed if Path(p).suffix.lower() in IMAGE_EXTS]
            if files:
                self._load_image_path(files[0])
                return
        self._set_main_status("剪贴板里没有图片，请先复制图片或截图", DANGER)

    def _on_display_image(self, path: str) -> None:
        self._load_image_path(Path(path))
        self.main_tabs.setCurrentIndex(SEND_TAB)
        self._set_main_status("已载入展示页图片，选联系人后可发阅后即焚", SUCCESS)

    def _load_image_path(self, path: Path) -> None:
        pix = QPixmap(str(path))
        if pix.isNull():
            QMessageBox.warning(self, "无法预览", "打不开这张图片")
            return
        self.image_path = path
        self._preview_pix = pix
        self.preview.setPixmap(
            pix.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.preview.setText("")
        self._set_main_status(f"已选择：{path.name}（可继续粘贴替换）", TEXT)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择要发送的图片", "", "图片 (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self._load_image_path(Path(path))

    def _clear_image(self) -> None:
        self.image_path = None
        self._preview_pix = None
        self.preview.setPixmap(QPixmap())
        self.preview.setText("选择或粘贴图片后在这里预览")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._preview_pix and not self._preview_pix.isNull():
            self.preview.setPixmap(
                self._preview_pix.scaled(
                    self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def _prepare_photo(self, src: Path) -> Path:
        img = Image.open(src)
        if img.mode != "RGB":
            img = img.convert("RGB")
        if max(img.size) > 2560:
            img.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
        dest = APP_DIR / "_upload_preview.jpg"
        img.save(dest, "JPEG", quality=92, optimize=True)
        return dest

    def _send(self) -> None:
        if self._busy:
            return
        if not self.selected:
            self._set_main_status("请先选择联系人", DANGER)
            return
        if not self.image_path or not self.image_path.exists():
            self._set_main_status("请先选择或粘贴图片", DANGER)
            return
        caption = self.caption_edit.text()
        user_id = int(self.selected["id"])
        name = self.selected["name"]
        src = self.image_path
        self._busy = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("正在发送…")
        self._set_main_status("正在上传并发送阅后即焚图片…", TEXT_DIM)

        def work():
            try:
                prepared = self._prepare_photo(src)
                self.runner.submit(
                    self.service.send_view_once(user_id, str(prepared), caption)
                ).result()
            except errors.TtlMediaInvalidError:
                self.call(lambda: self._finish_send(False, "该对话不支持阅后即焚（仅限私聊）"))
                return
            except errors.FloodWaitError as exc:
                self.call(
                    lambda: self._finish_send(False, f"操作过于频繁，请等待 {exc.seconds} 秒")
                )
                return
            except Exception as exc:
                self.call(lambda: self._finish_send(False, f"发送失败：{exc}"))
                return
            self.call(lambda: self._finish_send(True, f"已向 {name} 发送阅后即焚图片"))

        self._thread(work)

    def _finish_send(self, ok: bool, text: str) -> None:
        self._busy = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送阅后即焚")
        self._set_main_status(text, SUCCESS if ok else DANGER)

    def _logout(self) -> None:
        if (
            QMessageBox.question(
                self,
                "退出当前账号",
                "将退出当前 Telegram 账号，其他已登录账号不受影响。确定吗？",
            )
            != QMessageBox.Yes
        ):
            return
        self._backup_contacts()
        current_id = self.config_data.get("active_id")
        self._set_main_status("正在退出…", TEXT_DIM)

        def work():
            try:
                self.runner.submit(self.service.logout()).result()
            except Exception:
                pass
            self.call(lambda: self._after_logout(current_id))

        self._thread(work)

    def _after_logout(self, user_id: Any) -> None:
        if user_id is not None:
            self._remove_account(int(user_id))
        self.selected = None
        self._need_2fa = False
        self._login_busy = False
        self._clear_image()
        rest = self._accounts()
        self._rebuild_accounts()
        if rest:
            self._switch_account(int(rest[0]["id"]))
            return
        self._show_login()
        self._set_login_status("已退出，请登录账号", TEXT_DIM)
        self._connect(self._new_pending_session(), True)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._backup_contacts()
        except Exception:
            pass
        try:
            self.service.cancel_qr()
            self.runner.submit(self.service.disconnect())
        except Exception:
            pass
        for name in ("_upload_preview.jpg", "_clipboard.jpg", "_clipboard.png"):
            tmp = APP_DIR / name
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        self.runner.stop()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    icon = _window_icon()
    if icon:
        app.setWindowIcon(icon)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
