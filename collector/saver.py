from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import desc, select

from collector.collector import collect_messages
from collector.engine import get_db
from collector.models import RawMessages, Author
from collector.logger import logger
from collector.config import settings


async def get_or_create(session, model, search_params, create_params=None):
    query = select(model).filter_by(**search_params)
    obj = (await session.execute(query)).scalar_one_or_none()
    if obj:
        return obj, False
    all_params = {**(create_params or {}), **search_params}
    obj = model(**all_params)
    return obj, True


async def get_content_or_doc_spec(msg: dict) -> dict:
    if msg["msg_type"] == "text":
        return {"content": msg["text"]}
    if msg["msg_type"] == "voice":
        return {
            "file_id": msg["file_id"],
            "file_mime_type": msg["file_mime_type"],
        }
    if msg["msg_type"] == "photo":
        return {"file_id": msg["file_id"]}
    return {
        "file_id": msg["file_id"],
        "file_name": msg["file_name"],
        "file_mime_type": msg["file_mime_type"],
    }


async def check_old_data(session, message_thread, msgcr_time):
    lm_data = await last_msg_tuple_data(session, message_thread)
    lmcr_time = datetime.fromtimestamp(0) if lm_data[0] is None else lm_data[0]
    lmcr_session_num = lm_data[1]
    delta = timedelta(minutes=settings.MSG_SESSION_THRESHOLD[message_thread])
    return ((lmcr_time + delta) < msgcr_time, lmcr_session_num)


async def last_msg_tuple_data(session, message_thread) -> tuple:
    query = (
        select(RawMessages)
        .filter_by(message_thread=message_thread)
        .order_by(desc(RawMessages.id))
        .limit(1)
    )
    result = await session.execute(query)
    instance = result.scalar_one_or_none()
    return (
        (instance.created_at, instance.session_id) if instance else (None, 0)
    )


async def last_msg_session(session) -> int:
    query = select(RawMessages).order_by(desc(RawMessages.id)).limit(1)
    result = await session.execute(query)
    instance = result.scalar_one_or_none()
    return instance.session_id if instance else 0


async def raw_msgs_to_db(bot: Bot):
    # собираем последние сообщения из телеграм
    messages = await collect_messages(bot)
    
    async with get_db() as session:
        for msg in messages:
            msg_type = msg["msg_type"]

            author, create = await get_or_create(
                session=session,
                model=Author,
                search_params={"tlg_author_id": msg["author_id"]},
                create_params={
                    "author_name": settings.FAMILY_CHAT_IDS[msg["author_id"]],
                    "author_username": msg["author_username"],
                }
            )
            if create:
                session.add(author)

            # работаем теперь с RawMessages таблицей
            await session.flush()  # для получения author.id
            rw_msg_params = {
                "message_thread": msg["message_thread"],
                "msg_type": msg_type,
                "author_id": author.id,
            }

            message_content = await get_content_or_doc_spec(msg)
            rw_msg_params.update(message_content)

            # обрабатываем необязательные поля.
            if "forwarded_create_data" in msg:
                rw_msg_params.update(
                    {
                        "forwarded_create_data": datetime.fromtimestamp(
                            msg["forwarded_create_data"]
                        ),
                        "forwarded_msg_info": msg["forwarded_msg_info"],
                    }
                )
                # В пересланных сообщениях часто caption и есть содержание сообщения
                if msg.get("caption") and len(msg["caption"]) > 150:
                    rw_msg_params.update(
                        {
                            "content": msg["caption"]
                        }
                    )

            rw_msg, create = await get_or_create(
                session=session,
                model=RawMessages,
                search_params={"tlg_msg_id": msg["tlg_msg_id"]},
                create_params=rw_msg_params
            )

            if create:
                rw_msg.created_at = datetime.fromtimestamp(msg["created_at"])
                message_thread = msg["message_thread"]
                if message_thread in [
                    "diary",
                    "notes",
                ]:  # для них сложный способ обновления номера сессий
                    is_new_session, thread_session_num = await check_old_data(
                        session,
                        message_thread,
                        rw_msg.created_at,
                    )
                    session_id = (
                        await last_msg_session(session) + 1
                        if is_new_session
                        else thread_session_num
                    )
                else:
                    session_id = await last_msg_session(session) + 1

                rw_msg.session_id = session_id
                session.add(rw_msg)
                logger.debug(f"Создали новую запись: {rw_msg}")

        await session.commit()
