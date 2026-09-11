"""上分计算与本地「今日已增加」状态。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

MONEY_STEP = Decimal("1")
DEFAULT_RATE = Decimal("30")


def decimal_value(value: Any) -> Decimal:
    text = (
        str(value)
        .replace(",", "")
        .replace("，", "")
        .replace("¥", "")
        .replace("$", "")
        .replace("%", "")
        .strip()
    )
    return Decimal(text)


def plain_amount(value: Decimal) -> str:
    return f"{value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP):.0f}"


def money(value: Decimal) -> str:
    return f"{value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP):,.0f}"


def percent(value: Decimal) -> str:
    text = f"{value:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def local_now() -> datetime:
    return datetime.now().astimezone()


def increased_today(last_increased_at: str) -> bool:
    if not last_increased_at:
        return False
    try:
        last_date = datetime.fromisoformat(last_increased_at).astimezone().date()
        return last_date == local_now().date()
    except ValueError:
        return False


def next_amount(amount: Decimal, rate: Decimal) -> tuple[Decimal, Decimal]:
    increase = (amount * rate / Decimal("100")).quantize(
        MONEY_STEP, rounding=ROUND_HALF_UP
    )
    new_amount = (amount + increase).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    return increase, new_amount


class ScoreStore:
    """按当前登录账号 + Telegram user_id 记录上分时间。"""

    def __init__(self, app_dir: Path) -> None:
        self.path = app_dir / "data" / "score_state.json"
        self._data: dict[str, dict[str, str]] = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, str]] = {}
        for account_id, mapping in raw.items():
            if isinstance(mapping, dict):
                out[str(account_id)] = {
                    str(uid): str(when)
                    for uid, when in mapping.items()
                    if when
                }
        return out

    def last_increased_at(self, account_id: int, user_id: int) -> str:
        return self._data.get(str(account_id), {}).get(str(user_id), "")

    def mark(self, account_id: int, user_id: int, when: str) -> None:
        bucket = self._data.setdefault(str(account_id), {})
        bucket[str(user_id)] = when
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
