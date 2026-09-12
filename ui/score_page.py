from __future__ import annotations

from typing import Any

from PySide6.QtCore import QModelIndex, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from services.contact_name import format_contact_name
from services.score import ScoreStore, percent, plain_amount
from ui.score_delegates import ScoreActionDelegate, ScoreAvatarDelegate
from ui.score_model import ScoreContact, ScoreFilterModel, ScoreModel

TEXT_DIM = "#8b9bb0"
SUCCESS = "#34d399"
DANGER = "#fb7185"


class ScorePage(QWidget):
    increase_requested = Signal(object)
    need_avatars = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.account_id: int | None = None
        self.store: ScoreStore | None = None
        self._busy: set[int] = set()

        self.model = ScoreModel(self)
        self.proxy = ScoreFilterModel(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.horizontalHeader().setMinimumSectionSize(56)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.AVATAR, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.NAME, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.UID, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.AMOUNT, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.RATE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.STATUS, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(ScoreModel.ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(ScoreModel.AVATAR, 72)
        self.table.setColumnWidth(ScoreModel.UID, 96)
        self.table.setColumnWidth(ScoreModel.AMOUNT, 110)
        self.table.setColumnWidth(ScoreModel.ACTIONS, 152)
        self.table.setItemDelegateForColumn(ScoreModel.AVATAR, ScoreAvatarDelegate(self.table))
        self.action_delegate = ScoreActionDelegate(self.table)
        self.table.setItemDelegateForColumn(ScoreModel.ACTIONS, self.action_delegate)
        self.action_delegate.increase_requested.connect(self._on_increase)
        self.action_delegate.copy_requested.connect(self._on_copy)
        self.table.verticalScrollBar().valueChanged.connect(self._emit_visible_avatars)

        search = QLineEdit()
        search.setPlaceholderText("搜索名字或 UID")
        search.setClearButtonEnabled(True)
        search.setFixedWidth(240)
        search.textChanged.connect(self.proxy.set_query)
        search.textChanged.connect(self._refresh_count)

        title = QLabel("上分")
        title.setObjectName("h")
        self.count_label = QLabel()
        self.count_label.setObjectName("hint")
        tools = QHBoxLayout()
        tools.addWidget(title)
        tools.addWidget(self.count_label)
        tools.addStretch()
        tools.addWidget(search)

        self.empty_label = QLabel(
            "没有可上分的联系人\n通讯录备注需包含「名字 UID 金额」，例如：9.7 玛雅Patrick 20K 4772168 581"
        )
        self.empty_label.setObjectName("hint")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)

        frame = QFrame()
        frame.setObjectName("card")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.addWidget(self.table, 1)
        frame_layout.addWidget(self.empty_label)

        self.status = QLabel("从 Telegram 通讯录备注读取金额")
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(tools)
        layout.addWidget(frame, 1)
        layout.addWidget(self.status)

        self.model.modelReset.connect(self._refresh_count)
        self.proxy.rowsInserted.connect(self._refresh_count)
        self.proxy.rowsRemoved.connect(self._refresh_count)
        self._refresh_count()

    def set_status(self, text: str, color: str = TEXT_DIM) -> None:
        self.status.setText(text)
        self.status.setStyleSheet(f"color:{color};")

    def reset(self) -> None:
        self.account_id = None
        self._busy.clear()
        self.model.set_contacts([])
        self.set_status("从 Telegram 通讯录备注读取金额")

    def set_contacts(
        self,
        rows: list[dict[str, Any]],
        store: ScoreStore,
        account_id: int,
    ) -> None:
        self.store = store
        self.account_id = account_id
        contacts = [
            ScoreContact(
                user_id=int(row["id"]),
                name=str(row["name"]),
                uid=str(row["uid"]),
                amount=str(row["amount"]),
                rate=str(row["rate"]),
                last_increased_at=store.last_increased_at(account_id, int(row["id"])),
                raw_name=str(row.get("raw_name") or ""),
                username=str(row.get("username") or ""),
                phone=str(row.get("phone") or ""),
            )
            for row in rows
        ]
        self.model.set_contacts(contacts)
        self.set_status(f"可上分 {len(contacts)} 人（备注需含 UID 和金额）", SUCCESS)
        QTimer.singleShot(80, self._emit_visible_avatars)

    def set_avatar(self, user_id: int, data: bytes) -> None:
        self.model.set_avatar(user_id, data)

    def apply_increase(self, user_id: int, new_amount, when: str, raw_name: str = "") -> None:
        self._busy.discard(user_id)
        self.model.apply_increase(user_id, new_amount, when, raw_name)
        if self.store and self.account_id is not None:
            self.store.mark(self.account_id, user_id, when)

    def backup_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in self.model.contacts:
            username = (item.username or "").strip()
            if username and not username.startswith("@"):
                username = "@" + username
            raw = (item.raw_name or "").strip() or format_contact_name(
                item.name, item.uid, item.amount_decimal, item.rate_decimal
            )
            rows.append(
                {
                    "telegram_id": item.user_id,
                    "raw_name": raw,
                    "uid": item.uid,
                    "amount": plain_amount(item.amount_decimal),
                    "rate": percent(item.rate_decimal),
                    "username": username,
                    "phone": (item.phone or "").strip(),
                }
            )
        return rows

    def fail_increase(self, user_id: int, message: str) -> None:
        self._busy.discard(user_id)
        self.set_status(message, DANGER)

    def _contact_from_proxy(self, proxy_index: QModelIndex) -> ScoreContact | None:
        source = self.proxy.mapToSource(proxy_index)
        if not source.isValid():
            return None
        return self.model.contact_at(source.row())

    def _on_increase(self, proxy_index: QModelIndex) -> None:
        item = self._contact_from_proxy(proxy_index)
        if not item or item.user_id in self._busy:
            return
        self._busy.add(item.user_id)
        self.set_status(f"正在为 {item.name} 上分…", TEXT_DIM)
        self.increase_requested.emit(item)

    def _on_copy(self, proxy_index: QModelIndex) -> None:
        item = self._contact_from_proxy(proxy_index)
        if not item:
            return
        QApplication.clipboard().setText(f"{item.uid} {plain_amount(item.amount_decimal)}")
        self.set_status(f"已复制 {item.uid} {plain_amount(item.amount_decimal)}", SUCCESS)

    def _refresh_count(self, *_: Any) -> None:
        shown = self.proxy.rowCount()
        total = self.model.rowCount()
        self.count_label.setText(f"{shown} 人" if shown == total else f"{shown} / {total} 人")
        empty = shown == 0
        self.empty_label.setVisible(empty)
        self.table.setVisible(not empty)

    def _emit_visible_avatars(self, *_args) -> None:
        ids: list[int] = []
        view = self.table
        first = view.indexAt(QPoint(8, 8))
        last = view.indexAt(QPoint(8, max(8, view.viewport().height() - 8)))
        start = first.row() if first.isValid() else 0
        end = last.row() if last.isValid() else min(20, self.proxy.rowCount() - 1)
        for row in range(max(0, start), min(self.proxy.rowCount(), end + 4)):
            item = self._contact_from_proxy(self.proxy.index(row, 0))
            if item:
                ids.append(item.user_id)
        if ids:
            self.need_avatars.emit(ids)
