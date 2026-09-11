from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QModelIndex, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
)

from ui.score_model import ScoreModel

ACCENT = "#5ec8f0"
TEXT = "#f4f7fb"
HOVER_BG = "#1e3a4d"
AVATAR_BG = "#3d5a80"
BTN_BG = "#222838"
BORDER = "#2d3a52"


class ScoreAvatarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: Any, index: QModelIndex) -> None:
        item = index.data(ScoreModel.RawRole)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(HOVER_BG))
        size = min(42, option.rect.height() - 14, option.rect.width() - 14)
        avatar_rect = QRect(0, 0, size, size)
        avatar_rect.moveCenter(option.rect.center())
        pixmap = index.data(Qt.ItemDataRole.DecorationRole)
        if pixmap is None or pixmap.isNull():
            painter.setPen(QColor(BORDER))
            painter.setBrush(QColor(AVATAR_BG))
            painter.drawEllipse(avatar_rect)
            painter.setPen(QColor(TEXT))
            painter.drawText(
                avatar_rect,
                Qt.AlignmentFlag.AlignCenter,
                (item.name[:1].upper() if item and item.name else "?"),
            )
        else:
            path = QPainterPath()
            path.addEllipse(avatar_rect)
            painter.setClipPath(path)
            scaled = pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source = QRect(
                max(0, (scaled.width() - size) // 2),
                max(0, (scaled.height() - size) // 2),
                size,
                size,
            )
            painter.drawPixmap(avatar_rect, scaled, source)
        painter.restore()


class ScoreActionDelegate(QStyledItemDelegate):
    increase_requested = Signal(QModelIndex)
    copy_requested = Signal(QModelIndex)

    def _rects(self, option: Any) -> tuple[QRect, QRect]:
        area = option.rect.adjusted(8, 13, -8, -13)
        gap = 7
        width = max(56, (area.width() - gap) // 2)
        first = QRect(area)
        first.setWidth(width)
        second = QRect(area)
        second.setLeft(first.right() + gap)
        return first, second

    def paint(self, painter: QPainter, option: Any, index: QModelIndex) -> None:
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(HOVER_BG))
        increase_rect, copy_rect = self._rects(option)
        for rect, text, accent in (
            (increase_rect, "增加", True),
            (copy_rect, "复制", False),
        ):
            button = QStyleOptionButton()
            button.rect = rect
            button.text = text
            button.state = QStyle.StateFlag.State_Enabled
            if accent:
                button.palette.setColor(QPalette.ColorRole.Button, QColor(ACCENT))
                button.palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0c1218"))
            else:
                button.palette.setColor(QPalette.ColorRole.Button, QColor(BTN_BG))
                button.palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
            QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, button, painter)
        painter.restore()

    def editorEvent(self, event: QEvent, model: Any, option: Any, index: QModelIndex) -> bool:
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if not isinstance(event, QMouseEvent) or event.button() != Qt.MouseButton.LeftButton:
            return False
        position: QPoint = event.position().toPoint()
        increase_rect, copy_rect = self._rects(option)
        if increase_rect.contains(position):
            self.increase_requested.emit(index)
            return True
        if copy_rect.contains(position):
            self.copy_requested.emit(index)
            return True
        return False
