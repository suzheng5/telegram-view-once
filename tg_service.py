"""Telegram MTProto 会话与发图逻辑。"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from telethon import TelegramClient, functions, types, utils
from telethon.tl.types import User

from services.contact_name import parse_contact_name, split_contact_name


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
CONFIG_PATH = APP_DIR / "config.json"
SESSIONS_DIR = APP_DIR / "sessions"
LEGACY_SESSION = str(APP_DIR / "telegram_session")
VIEW_ONCE_TTL = 0x7FFFFFFF
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_config(data: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class AsyncRunner:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)


class TelegramService:
    def __init__(self) -> None:
        self.client: TelegramClient | None = None
        self.session_path = ""
        self._qr_cancel = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, api_id: int, api_hash: str, session_path: str) -> bool:
        if self.client:
            await self.disconnect()
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._loop = asyncio.get_running_loop()
        self.session_path = session_path
        self.client = TelegramClient(session_path, api_id, api_hash)
        await self.client.connect()
        return await self.client.is_user_authorized()

    async def disconnect(self) -> None:
        self.cancel_qr()
        if self.client:
            await self.client.disconnect()
            self.client = None

    def cancel_qr(self) -> None:
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._qr_cancel.set)
        else:
            self._qr_cancel.set()

    async def me(self) -> dict[str, Any]:
        assert self.client
        user = await self.client.get_me()
        name = utils.get_display_name(user) or "我"
        username = f"@{user.username}" if user.username else ""
        return {"id": user.id, "name": name, "username": username}

    async def qr_login(
        self, on_url: Callable[[str], None], ignored_ids: list[int] | None = None
    ) -> None:
        assert self.client
        self._qr_cancel = asyncio.Event()
        qr = await self.client.qr_login(ignored_ids=ignored_ids or [])
        on_url(qr.url)
        while not self._qr_cancel.is_set():
            wait_task = asyncio.create_task(qr.wait())
            cancel_task = asyncio.create_task(self._qr_cancel.wait())
            done, pending = await asyncio.wait(
                {wait_task, cancel_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            if self._qr_cancel.is_set():
                raise asyncio.CancelledError()
            try:
                await wait_task
                return
            except asyncio.TimeoutError:
                await qr.recreate()
                on_url(qr.url)

    async def send_code(self, phone: str):
        assert self.client
        return await self.client.send_code_request(phone)

    async def sign_in_code(self, phone: str, code: str) -> None:
        assert self.client
        await self.client.sign_in(phone=phone, code=code)

    async def sign_in_password(self, password: str) -> None:
        assert self.client
        await self.client.sign_in(password=password)
        if not await self.client.is_user_authorized():
            raise RuntimeError("密码已提交，但账号仍未登录，请重试")

    @staticmethod
    def _preview_text(dialog) -> str:
        msg = dialog.message
        if not msg:
            return ""
        text = (msg.message or "").replace("\n", " ").strip()
        if text:
            return text[:40]
        if getattr(msg, "photo", None):
            return "[图片]"
        if getattr(msg, "video", None):
            return "[视频]"
        if getattr(msg, "sticker", None):
            return "[贴纸]"
        if getattr(msg, "document", None):
            return "[文件]"
        return ""

    async def list_private_chats(self, limit: int = 300) -> list[dict[str, Any]]:
        assert self.client
        dialogs = await self.client.get_dialogs(limit=limit)
        chats: list[dict[str, Any]] = []
        for dialog in dialogs:
            entity = dialog.entity
            if not isinstance(entity, User):
                continue
            if entity.bot or entity.deleted:
                continue
            name = "收藏夹" if entity.is_self else (utils.get_display_name(entity) or "未命名")
            when = dialog.date
            time_text = when.strftime("%m-%d %H:%M") if isinstance(when, datetime) else ""
            chats.append(
                {
                    "id": entity.id,
                    "name": name,
                    "username": entity.username or "",
                    "phone": entity.phone or "",
                    "time": time_text,
                    "preview": self._preview_text(dialog),
                    "is_self": bool(entity.is_self),
                }
            )
        return chats

    @staticmethod
    def _saved_name(user: User) -> str:
        parts = [p for p in (user.first_name or "", user.last_name or "") if p]
        return " ".join(parts).strip() or (utils.get_display_name(user) or "")

    def _score_row(self, user: User, display_name: str) -> dict[str, Any] | None:
        parsed = parse_contact_name(display_name)
        if not parsed:
            return None
        username = f"@{user.username}" if user.username else ""
        return {
            "id": user.id,
            "name": parsed.name,
            "uid": parsed.uid,
            "amount": str(parsed.amount),
            "rate": str(parsed.rate),
            "username": username,
            "phone": user.phone or "",
            "raw_name": display_name.strip(),
        }

    @staticmethod
    def sort_scores_like_chats(
        scores: list[dict[str, Any]], chats: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rank = {int(chat["id"]): i for i, chat in enumerate(chats)}
        last = len(rank)
        return sorted(scores, key=lambda row: rank.get(int(row["id"]), last))

    async def list_score_contacts(self) -> list[dict[str, Any]]:
        assert self.client
        rows: list[dict[str, Any]] = []
        try:
            result = await self.client(functions.contacts.GetContactsRequest(hash=0))
            users = getattr(result, "users", None) or []
        except Exception:
            return rows
        for user in users:
            if not isinstance(user, User) or user.bot or user.deleted or user.is_self:
                continue
            row = self._score_row(user, self._saved_name(user))
            if row:
                rows.append(row)
        return rows

    async def update_contact_name(self, user_id: int, display_name: str) -> None:
        assert self.client
        peer = await self.client.get_input_entity(user_id)
        entity = await self.client.get_entity(user_id)
        phone = getattr(entity, "phone", None) or ""
        first, last = split_contact_name(display_name)
        await self.client(
            functions.contacts.AddContactRequest(
                id=peer,
                first_name=first,
                last_name=last,
                phone=phone,
                add_phone_privacy_exception=False,
            )
        )

    async def avatar_bytes(self, user_id: int) -> bytes | None:
        assert self.client
        try:
            data = await self.client.download_profile_photo(
                user_id, file=bytes, download_big=False
            )
            return data or None
        except Exception:
            return None

    async def fetch_avatars(
        self, user_ids: list[int], on_one: Callable[[int, bytes], None]
    ) -> None:
        sem = asyncio.Semaphore(4)

        async def one(uid: int) -> None:
            async with sem:
                data = await self.avatar_bytes(uid)
                if data:
                    on_one(uid, data)

        await asyncio.gather(*(one(uid) for uid in user_ids), return_exceptions=True)

    async def send_view_once(
        self, user_id: int, file_path: str, caption: str = ""
    ) -> None:
        assert self.client
        peer = await self.client.get_input_entity(user_id)
        uploaded = await self.client.upload_file(file_path)
        await self.client(
            functions.messages.SendMediaRequest(
                peer=peer,
                media=types.InputMediaUploadedPhoto(
                    file=uploaded,
                    ttl_seconds=VIEW_ONCE_TTL,
                ),
                message=caption.strip(),
                random_id=int.from_bytes(os.urandom(8), "big", signed=True),
            )
        )

    async def adopt_session(self, user_id: int, api_id: int, api_hash: str) -> str:
        old = self.session_path
        dest = str(SESSIONS_DIR / str(user_id))
        if Path(old + ".session").resolve() == Path(dest + ".session").resolve():
            return dest
        await self.disconnect()
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        for suffix in (".session", ".session-journal"):
            src = Path(old + suffix)
            dst = Path(dest + suffix)
            if not src.exists():
                continue
            if dst.exists():
                dst.unlink()
            shutil.move(str(src), str(dst))
        await self.connect(api_id, api_hash, dest)
        return dest

    async def logout(self) -> None:
        session_path = self.session_path
        if self.client:
            try:
                await self.client.log_out()
            except Exception:
                await self.disconnect()
            self.client = None
        if not session_path:
            return
        for extra in Path(session_path).parent.glob(Path(session_path).name + ".session*"):
            try:
                extra.unlink()
            except OSError:
                pass
