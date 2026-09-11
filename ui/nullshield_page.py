from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nullshield.config_store import load_config, save_config
from nullshield.html_capture import capture_html_png
from nullshield.html_render import format_money
from nullshield.page_builder import (
    PAGE_COPY_LABELS,
    PAGE_FILES,
    PAGE_OPEN_LABELS,
    build_all_pages,
    build_page,
)
from nullshield.paths import OUTPUT_DIR

TEXT_DIM = "#8b9bb0"
SUCCESS = "#34d399"
DANGER = "#fb7185"


class NullShieldPage(QWidget):
    image_ready = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_data = load_config()
        self._fields: dict[str, QLineEdit] = {}
        self._totals: dict[str, QLabel] = {}
        self._busy = False
        self._build()
        self._load_fields()

    def _btn(self, text: str, handler, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        if primary:
            btn.setObjectName("primary")
        btn.clicked.connect(handler)
        return btn

    def _add_field(self, form: QFormLayout, label: str, key: str) -> None:
        edit = QLineEdit()
        self._fields[key] = edit
        if key in ("fund_principal", "fund_profit", "fund_re_prior", "fund_re_additional"):
            edit.textChanged.connect(self._update_totals)
        form.addRow(label, edit)

    def _group(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setSpacing(8)
        return box, form

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("展示页面")
        title.setObjectName("h")
        hint = QLabel("填参数后点复制，图片会进剪贴板并带到发图页，可直接发阅后即焚。不含追踪展示。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 4, 0)
        col.setSpacing(8)

        fund, ff = self._group("资金追踪")
        self._add_field(ff, "本金投入 (USD)", "fund_principal")
        self._add_field(ff, "盈利收入 (USD)", "fund_profit")
        total = QLabel()
        total.setObjectName("ok")
        self._totals["fund_total"] = total
        ff.addRow(total)
        col.addWidget(fund)

        extra, ef = self._group("资金追回 · 额外暴露")
        self._add_field(ef, "已追踪资金 (USD)", "fund_re_prior")
        self._add_field(ef, "额外发现资金 (USD)", "fund_re_additional")
        extra_hint = QLabel("已追踪留空则自动用上方本金 + 盈利")
        extra_hint.setObjectName("hint")
        extra_hint.setWordWrap(True)
        ef.addRow(extra_hint)
        combined = QLabel()
        combined.setObjectName("ok")
        self._totals["fund_re_combined"] = combined
        ef.addRow(combined)
        col.addWidget(extra)

        fw, wf = self._group("防火墙警告")
        self._add_field(wf, "剩余可交易次数", "fw_tx_remaining")
        self._add_field(wf, "账户余额要求 (USD)", "fw_balance_threshold")
        col.addWidget(fw)

        fi, inf = self._group("防火墙-入侵")
        self._add_field(inf, "防御时长 - 小时", "fi_hold_hours")
        self._add_field(inf, "防御时长 - 分钟", "fi_hold_minutes")
        self._add_field(inf, "防御时长 - 秒", "fi_hold_seconds")
        fi_hint = QLabel("关闭时间 = 打开页面时的本地时间 + 上述时长")
        fi_hint.setObjectName("hint")
        inf.addRow(fi_hint)
        col.addWidget(fi)

        for title_text, note in (
            ("提款警告", "无需额外参数，直接打开或复制即可。"),
            ("小额交易警告", "无需额外参数，直接打开或复制即可。"),
        ):
            box, form = self._group(title_text)
            note_label = QLabel(note)
            note_label.setObjectName("hint")
            form.addRow(note_label)
            col.addWidget(box)

        col.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        panel = QFrame()
        panel.setObjectName("card")
        actions = QVBoxLayout(panel)
        actions.setContentsMargins(12, 12, 12, 12)
        actions.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(self._btn("保存配置", self._save, primary=True))
        top.addWidget(self._btn("生成全部", self._build_all))
        top.addStretch()
        actions.addLayout(top)
        actions.addWidget(self._label("打开页面"))
        actions.addLayout(self._page_grid(PAGE_OPEN_LABELS, self._open_page))
        actions.addWidget(self._label("复制页面（发图）"))
        actions.addLayout(self._page_grid(PAGE_COPY_LABELS, self._copy_page))
        root.addWidget(panel)

        self.status = QLabel("改完参数后先复制再发图")
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def _label(self, text: str) -> QLabel:
        item = QLabel(text)
        item.setObjectName("hint")
        return item

    def _page_grid(self, labels: dict[str, str], handler) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for idx, key in enumerate(PAGE_FILES):
            btn = QPushButton(labels[key])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=key: handler(k))
            grid.addWidget(btn, idx // 3, idx % 3)
        return grid

    def _parse_amount(self, value: str) -> float:
        try:
            return float(str(value).replace(",", "").strip() or 0)
        except ValueError:
            return 0.0

    def _resolved_prior(self) -> float:
        prior = self._parse_amount(self._fields["fund_re_prior"].text())
        if prior > 0:
            return prior
        return self._parse_amount(self._fields["fund_principal"].text()) + self._parse_amount(
            self._fields["fund_profit"].text()
        )

    def _update_totals(self) -> None:
        fund_total = format_money(
            self._parse_amount(self._fields["fund_principal"].text())
            + self._parse_amount(self._fields["fund_profit"].text())
        )
        self._totals["fund_total"].setText(f"损失总额：{fund_total}（本金 + 盈利）")
        combined = format_money(
            self._resolved_prior() + self._parse_amount(self._fields["fund_re_additional"].text())
        )
        self._totals["fund_re_combined"].setText(f"合并追回总额：{combined}")

    def _load_fields(self) -> None:
        cfg = self.config_data
        mapping = {
            "fund_principal": cfg["fund_trace"]["principal"],
            "fund_profit": cfg["fund_trace"]["profit"],
            "fund_re_prior": cfg["fund_recovery_extra"]["prior_traced"],
            "fund_re_additional": cfg["fund_recovery_extra"]["additional_found"],
            "fw_tx_remaining": cfg["firewall"]["tx_remaining"],
            "fw_balance_threshold": cfg["firewall"]["balance_threshold"],
            "fi_hold_hours": cfg["firewall_intrusion"]["hold_hours"],
            "fi_hold_minutes": cfg["firewall_intrusion"]["hold_minutes"],
            "fi_hold_seconds": cfg["firewall_intrusion"]["hold_seconds"],
        }
        for key, value in mapping.items():
            self._fields[key].setText(str(value))
        self._update_totals()

    def _collect_config(self) -> dict[str, Any]:
        return {
            "fund_trace": {
                "principal": self._fields["fund_principal"].text().strip(),
                "profit": self._fields["fund_profit"].text().strip(),
            },
            "fund_recovery_extra": {
                "prior_traced": self._fields["fund_re_prior"].text().strip(),
                "additional_found": self._fields["fund_re_additional"].text().strip(),
            },
            "firewall": {
                "tx_remaining": self._fields["fw_tx_remaining"].text().strip(),
                "balance_threshold": self._fields["fw_balance_threshold"].text().strip(),
            },
            "firewall_intrusion": {
                "hold_hours": self._fields["fi_hold_hours"].text().strip(),
                "hold_minutes": self._fields["fi_hold_minutes"].text().strip(),
                "hold_seconds": self._fields["fi_hold_seconds"].text().strip(),
            },
        }

    def _persist(self) -> dict[str, Any]:
        self.config_data = self._collect_config()
        save_config(self.config_data)
        return self.config_data

    def set_status(self, text: str, color: str = TEXT_DIM) -> None:
        self.status.setText(text)
        self.status.setStyleSheet(f"color:{color};")

    def _save(self) -> None:
        self._persist()
        self.set_status("配置已保存", SUCCESS)

    def _build_all(self) -> None:
        try:
            paths = build_all_pages(self._persist())
        except Exception as exc:
            self.set_status(f"生成失败：{exc}", DANGER)
            return
        self.set_status(f"已生成 {len(paths)} 个页面到 output 目录", SUCCESS)

    def _open_page(self, page_key: str) -> None:
        try:
            path = build_page(page_key, self._persist())
            webbrowser.open(path.resolve().as_uri())
            self.set_status(f"已打开 {PAGE_OPEN_LABELS[page_key]}", SUCCESS)
        except Exception as exc:
            self.set_status(f"打开失败：{exc}", DANGER)

    def _copy_page(self, page_key: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.set_status(f"正在生成 {PAGE_COPY_LABELS[page_key]} …", TEXT_DIM)
        try:
            html_path = build_page(page_key, self._persist())
            png_path = OUTPUT_DIR / f"{page_key}.png"
            capture_html_png(html_path, png_path)
            image = QImage(str(png_path))
            if image.isNull():
                raise RuntimeError("截出来的图片打不开")
            QGuiApplication.clipboard().setImage(image)
            self.image_ready.emit(str(png_path))
            self.set_status(f"已复制 {PAGE_COPY_LABELS[page_key]}，可到发图页发送", SUCCESS)
        except Exception as exc:
            self.set_status(f"复制失败：{exc}", DANGER)
        finally:
            self._busy = False
