"""从 Telegram 通讯录备注解析 / 回写 上分字段。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from services.score import DEFAULT_RATE, percent, plain_amount

_RATE_RE = re.compile(r"^(\d{1,4}(?:\.\d+)?)%?$")
_TG_NAME_MAX = 64


@dataclass(frozen=True)
class ParsedContact:
    name: str
    uid: str
    amount: Decimal
    rate: Decimal


def _is_uid(token: str) -> bool:
    return token.isdigit() and len(token) == 7


def _is_amount(token: str) -> bool:
    cleaned = token.replace(",", "").replace("，", "")
    return bool(cleaned) and cleaned.isdigit()


def _parse_amount(token: str) -> Decimal:
    return Decimal(token.replace(",", "").replace("，", ""))


def _parse_rate(token: str) -> Decimal | None:
    match = _RATE_RE.fullmatch(token.strip())
    if not match:
        return None
    return Decimal(match.group(1))


def parse_contact_name(display_name: str) -> ParsedContact | None:
    """从右解析：名字 … UID(7位) 金额 [倍率]。倍率缺省 30%。"""
    tokens = (display_name or "").split()
    if len(tokens) < 3:
        return None

    end = len(tokens)
    rate = DEFAULT_RATE
    if end >= 4:
        maybe_rate = _parse_rate(tokens[end - 1])
        if (
            maybe_rate is not None
            and _is_amount(tokens[end - 2])
            and _is_uid(tokens[end - 3])
        ):
            rate = maybe_rate
            end -= 1

    if end < 3 or not _is_amount(tokens[end - 1]) or not _is_uid(tokens[end - 2]):
        return None
    name = " ".join(tokens[: end - 2]).strip()
    if not name:
        return None
    return ParsedContact(
        name=name,
        uid=tokens[end - 2],
        amount=_parse_amount(tokens[end - 1]),
        rate=rate,
    )


def format_contact_name(name: str, uid: str, amount: Decimal, rate: Decimal) -> str:
    parts = [name.strip(), str(uid).strip(), plain_amount(amount)]
    if rate != DEFAULT_RATE:
        parts.append(percent(rate))
    return " ".join(parts)


def split_contact_name(full: str) -> tuple[str, str]:
    """Telegram first_name / last_name 各最多 64 字符。"""
    text = (full or "").strip()
    if len(text) <= _TG_NAME_MAX:
        return text, ""
    return text[:_TG_NAME_MAX], text[_TG_NAME_MAX : _TG_NAME_MAX * 2]
