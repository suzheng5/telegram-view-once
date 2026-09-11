"""把上分联系人备份到软件目录，换号后仍可从本地找回。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _prefer(new: Any, old: Any) -> str:
    return _text(new) or _text(old)


def _normalize(row: dict[str, Any]) -> dict[str, Any] | None:
    telegram_id = int(row.get("telegram_id") or 0)
    if telegram_id <= 0:
        return None
    username = _text(row.get("username"))
    if username and not username.startswith("@"):
        username = "@" + username
    return {
        "telegram_id": telegram_id,
        "raw_name": _text(row.get("raw_name")),
        "uid": _text(row.get("uid")),
        "amount": _text(row.get("amount")),
        "rate": _text(row.get("rate")),
        "username": username,
        "phone": _text(row.get("phone")),
        "avatar": _text(row.get("avatar")),
    }


def merge_contacts(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}
    for row in existing:
        item = _normalize(row)
        if item:
            by_id[item["telegram_id"]] = item
    for row in incoming:
        item = _normalize(row)
        if not item:
            continue
        old = by_id.get(item["telegram_id"], {})
        by_id[item["telegram_id"]] = {
            "telegram_id": item["telegram_id"],
            "raw_name": item["raw_name"] or old.get("raw_name", ""),
            "uid": item["uid"] or old.get("uid", ""),
            "amount": item["amount"] or old.get("amount", ""),
            "rate": item["rate"] or old.get("rate", ""),
            "username": _prefer(item["username"], old.get("username")),
            "phone": _prefer(item["phone"], old.get("phone")),
            "avatar": item["avatar"] or old.get("avatar", ""),
        }
    return list(by_id.values())


class ContactBackup:
    def __init__(self, app_dir: Path) -> None:
        self.root = app_dir / "data" / "contacts_backup"

    def account_dir(self, account_id: int) -> Path:
        return self.root / str(int(account_id))

    def json_path(self, account_id: int) -> Path:
        return self.account_dir(account_id) / "contacts.json"

    def avatar_dir(self, account_id: int) -> Path:
        return self.account_dir(account_id) / "avatars"

    def avatar_file(self, account_id: int, telegram_id: int) -> Path:
        return self.avatar_dir(account_id) / f"{int(telegram_id)}.jpg"

    def load(self, account_id: int) -> list[dict[str, Any]]:
        path = self.json_path(account_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        contacts = raw.get("contacts") if isinstance(raw, dict) else raw
        if not isinstance(contacts, list):
            return []
        return [item for item in (_normalize(row) for row in contacts if isinstance(row, dict)) if item]

    def load_avatars(self, account_id: int) -> dict[int, bytes]:
        folder = self.avatar_dir(account_id)
        if not folder.exists():
            return {}
        out: dict[int, bytes] = {}
        for path in folder.glob("*.jpg"):
            if not path.stem.isdigit():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if data:
                out[int(path.stem)] = data
        return out

    def save_avatar(self, account_id: int, telegram_id: int, data: bytes) -> str:
        path = self.avatar_file(account_id, telegram_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"avatars/{int(telegram_id)}.jpg"

    def save(self, account_id: int, incoming: list[dict[str, Any]]) -> int:
        merged = merge_contacts(self.load(account_id), incoming)
        if not merged:
            return 0
        for row in merged:
            if self.avatar_file(account_id, int(row["telegram_id"])).exists():
                row["avatar"] = f"avatars/{int(row['telegram_id'])}.jpg"
        payload = {
            "account_id": int(account_id),
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "contacts": merged,
        }
        path = self.json_path(account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        return len(merged)
