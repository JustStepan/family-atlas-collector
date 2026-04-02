from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class SessionStatus(Enum):
    READY = 'ready'
    DONE = 'done'
    ERROR = 'error'


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    pass


class Author(Base):
    __tablename__ = 'authors'

    tlg_author_id: Mapped[int] = mapped_column(Integer)
    author_name: Mapped[str] = mapped_column(String(50))
    author_username: Mapped[str] = mapped_column(String(50))
    raw_msgs: Mapped[list['RawMessages']] = relationship(back_populates="author")

    def __repr__(self) -> str:
        return f"Автор(id={self.id}, Имя={self.author_name!r})"


class RawMessages(Base):
    __tablename__ = 'rwmsgs'
    
    # обязательные поля
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped["Author"] = relationship(back_populates="raw_msgs")
    session_id: Mapped[int] = mapped_column(Integer)
    tlg_msg_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime]
    msg_type: Mapped[str] = mapped_column(String(12), default='text')
    message_thread: Mapped[str] = mapped_column(String(10), default='notes')
    session_status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus),
        default=SessionStatus.READY
    )
    
    # content будет зависеть от типа msg_type:
    # content=text(для text); content=doc_id(для document);
    # content=photo_id(для photo); content=voice_id(для voice);
    content: Mapped[str | None] = mapped_column(Text, default=None)
    # Поля не обязательные (для опционального заполнения)
    caption: Mapped[str | None] = mapped_column(String, default=None)
    # documents_spec
    file_mime_type: Mapped[str | None] = mapped_column(String, default=None)
    file_name: Mapped[str | None] = mapped_column(String, default=None)
    file_id: Mapped[str | None] = mapped_column(String, default=None)

    # forwarded messages 
    forwarded_create_data: Mapped[datetime | None]
    forwarded_msg_info: Mapped[str | None] = mapped_column(String, default=None)

    def __repr__(self) -> str:
        message = f"RAW_Сообщение(id={self.id}, Сессия={self.session_id!r}, Тип={self.msg_type!r}, Тип={self.message_thread!r})"
        return message + f'Content={self.content[:25]}' if self.content else message
