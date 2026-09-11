from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QColor, QPixmap

from services.score import decimal_value, increased_today, money, percent

ACCENT_STATUS = "#34d399"
DIM_STATUS = "#8b9bb0"


@dataclass
class ScoreContact:
    user_id: int
    name: str
    uid: str
    amount: str
    rate: str
    last_increased_at: str = ""
    raw_name: str = ""
    username: str = ""
    phone: str = ""

    @property
    def amount_decimal(self) -> Decimal:
        return decimal_value(self.amount)

    @property
    def rate_decimal(self) -> Decimal:
        return decimal_value(self.rate)

    def increased_today(self) -> bool:
        return increased_today(self.last_increased_at)


class ScoreModel(QAbstractTableModel):
    HEADERS = ("头像", "名字", "UID", "金额", "倍率", "今日状态", "操作")
    AVATAR, NAME, UID, AMOUNT, RATE, STATUS, ACTIONS = range(7)
    RawRole = Qt.ItemDataRole.UserRole + 1

    changed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.contacts: list[ScoreContact] = []
        self._avatars: dict[int, QPixmap] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.contacts)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self.contacts):
            return None
        item = self.contacts[index.row()]
        column = index.column()
        if role == self.RawRole:
            return item
        if role == Qt.ItemDataRole.DisplayRole:
            if column == self.NAME:
                return item.name
            if column == self.UID:
                return item.uid
            if column == self.AMOUNT:
                return money(item.amount_decimal)
            if column == self.RATE:
                return f"{percent(item.rate_decimal)} %"
            if column == self.STATUS:
                return "今日已增加" if item.increased_today() else "今日未增加"
            return ""
        if role == Qt.ItemDataRole.ToolTipRole:
            if column == self.AMOUNT:
                bump = item.amount_decimal * item.rate_decimal / Decimal("100")
                return f"下次增加 {money(bump)}"
            if column == self.NAME:
                return item.name
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in (self.AMOUNT, self.RATE, self.UID):
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        if role == Qt.ItemDataRole.ForegroundRole and column == self.STATUS:
            return QColor(ACCENT_STATUS) if item.increased_today() else QColor(DIM_STATUS)
        if role == Qt.ItemDataRole.DecorationRole and column == self.AVATAR:
            return self._avatars.get(item.user_id)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def set_contacts(self, contacts: list[ScoreContact]) -> None:
        self.beginResetModel()
        self.contacts = contacts
        self._avatars.clear()
        self.endResetModel()

    def contact_at(self, row: int) -> ScoreContact:
        return self.contacts[row]

    def apply_increase(self, user_id: int, new_amount: Decimal, when: str, raw_name: str = "") -> None:
        for row, item in enumerate(self.contacts):
            if item.user_id != user_id:
                continue
            item.amount = str(new_amount)
            item.last_increased_at = when
            if raw_name:
                item.raw_name = raw_name
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
            return

    def set_avatar(self, user_id: int, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data):
            return
        pix = pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self._avatars[user_id] = pix
        for row, item in enumerate(self.contacts):
            if item.user_id == user_id:
                idx = self.index(row, self.AVATAR)
                self.dataChanged.emit(idx, idx)
                break


class ScoreFilterModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.query = ""
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_query(self, text: str) -> None:
        self.query = text.strip().casefold()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self.query:
            return True
        model = self.sourceModel()
        index = model.index(source_row, ScoreModel.NAME, source_parent)
        item = model.data(index, ScoreModel.RawRole)
        if not item:
            return False
        return self.query in item.name.casefold() or self.query in item.uid.casefold()
