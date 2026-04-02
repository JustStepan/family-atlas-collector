from typing import Any

from aiogram import Bot
from aiogram.types import Update
from sqlalchemy import desc, select

from collector.config import settings
from collector.engine import get_db
from collector.models import RawMessages
from collector.logger import logger


THREAD_MAPS = {
    2: "diary",
    4: "calendar",
    6: "notes",
    8: "task",
}


CONTENT_EXTRACTORS = {
    "text": lambda msg: {"text": msg.text},
    "photo": lambda msg: {"file_id": msg.photo[-1].file_id},
    "voice": lambda msg: {
        "file_id": msg.voice.file_id,
        "file_mime_type": msg.voice.mime_type,
    },
    "document": lambda msg: {
        "file_id": msg.document.file_id,
        "file_mime_type": msg.document.mime_type,
        "file_name": msg.document.file_name,
    },
    "video": lambda msg: {
        "file_id": msg.video.file_id,
        "file_mime_type": msg.video.mime_type,
        "file_name": msg.video.file_name,
    },
}


async def get_last_update_id() -> int:
    async with get_db() as session:
        query = (
            select(RawMessages.tlg_msg_id)
            .order_by(desc(RawMessages.id))
            .limit(1)
        )
        result = await session.execute(query)
        last_id = result.scalar_one_or_none()
        return last_id if last_id else 0


def detect_msg_type(msg) -> str | None:
    return next(
        (attr for attr in settings.MSG_TYPES if getattr(msg, attr)),
        None
    )


def get_content(msg_type: str, msg):
    return CONTENT_EXTRACTORS[msg_type](msg)


async def collect_messages(bot: Bot) -> list[dict[str, Any]]:
    last_update_id = await get_last_update_id()
    updates: list[Update] = await bot.get_updates(
        offset=last_update_id + 1,
        limit=100,
        timeout=0,
    )
    if len(updates) != 0:
        logger.info(f"Получено {len(updates)} сообщений")

    collected = []
    for update in updates:
        # пропускаем если нет message
        if not update.message:
            continue
        msg = update.message

        # пропускаем если нет message_thread_id
        if not msg.message_thread_id:
            continue

        # пропускаем если тред не в нашей карте
        message_thread = THREAD_MAPS.get(msg.message_thread_id)
        if not message_thread:
            logger.error(f"Неизвестный thread_id: {msg.message_thread_id}")
            continue

        # определяем тип сообщения
        msg_type = detect_msg_type(msg)
        if not msg_type:
            logger.error(f"Неизвестный тип: {update.update_id}")
            continue

        author_id = msg.from_user.id
        author_name = settings.FAMILY_CHAT_IDS.get(author_id)
        if not author_name:
            raise ValueError(f"Неизвестный автор: {author_id}. Проверь FAMILY_CHAT_IDS")

        final_dict = {
            "tlg_msg_id": update.update_id,
            "msg_type": msg_type,
            "author_id": author_id,
            "author_username": msg.from_user.username,
            "author_name": author_name,
            "message_thread": message_thread,
            "created_at": msg.date.timestamp(),
        }

        # контент по типу
        final_dict.update(get_content(msg_type, msg))

        # пересланные сообщения
        if msg.forward_origin:
            final_dict.update(await handle_forwarded(msg))

        # caption
        if msg.caption:
            final_dict["caption"] = msg.caption

        collected.append(final_dict)

    return collected


async def handle_forwarded(msg) -> dict:
    result = {"forwarded_create_data": msg.forward_origin.date.timestamp()}
    origin = msg.forward_origin

    if hasattr(origin, "sender_user") and origin.sender_user:
        user = origin.sender_user
        if user.id == msg.from_user.id:
            info = "Автор переслал своё собственное сообщение"
        elif user.id in settings.FAMILY_CHAT_IDS:
            info = f"Автор переслал сообщение от {settings.FAMILY_CHAT_IDS[user.id]}"
        else:
            info = f"Автор переслал сообщение от {user.first_name}, @{user.username}"
        result["forwarded_msg_info"] = info

    if hasattr(origin, "chat") and origin.chat:
        chat = origin.chat
        username = getattr(chat, "username", None)
        if username:
            info = f"Переслано из канала '{chat.title}', @{username}"
        else:
            info = f"Переслано из чата '{chat.title}'"
        result["forwarded_msg_info"] = info

    return result