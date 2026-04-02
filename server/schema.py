from datetime import datetime

from pydantic import BaseModel


class Author(BaseModel):
    id: int
    tlg_author_id: int
    author_name: str
    author_username: str

    model_config = {"from_attributes": True}


class RawMessagesSchema(BaseModel):

    id: int
    author_id: int
    author: Author
    session_id: int
    message_thread: str
    session_status: str

    content: str | None
    caption: str | None
    file_mime_type: str | None
    file_name: str | None
    file_id: str | None

    forwarded_create_data: datetime | None
    forwarded_msg_info: str | None

    model_config = {"from_attributes": True}


class DoneMessages(BaseModel):
    ids: list[int]
