from fastapi import Depends, FastAPI

from sqlalchemy import update, select
from sqlalchemy.orm import joinedload

from collector.engine import get_db
from collector.logger import logger
from collector.models import RawMessages, SessionStatus
from server.schema import DoneMessages, RawMessagesSchema
from server.validation import verify_api_key

app = FastAPI()


@app.get(
        '/messages/ready/',
        response_model=list[RawMessagesSchema],
        dependencies=[Depends(verify_api_key)]
)
async def get_ready_messages():
    async with get_db() as session:
        query = (
            select(RawMessages)
            .options(joinedload(RawMessages.author))
            .filter_by(session_status=SessionStatus.READY)
        )
        result = await session.execute(query)
        messages = result.scalars().all()
        return [RawMessagesSchema.model_validate(m) for m in messages]


@app.post('/messages/done/', dependencies=[Depends(verify_api_key)])
async def change_msgs_status(request: DoneMessages):
    if request.ids is None:
        return
    
    async with get_db() as session:
        try:
            query = (
                update(RawMessages)
                .where(RawMessages.id.in_(request.ids))
                .values(session_status=SessionStatus.DONE)
            )
            await session.execute(query)
            await session.commit()
            return {"message": "ok"}
        except Exception as e:
            logger.error(f'Ошибка: {e} при попытке обновить статусы')
            return {"message": "error"}