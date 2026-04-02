from contextlib import asynccontextmanager

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from collector.config import BASE_DIR
from collector.logger import logger

from collector.models import Base


DB_DIR = BASE_DIR / 'family-atlas.db'
engine = create_async_engine(f'sqlite+aiosqlite:///{DB_DIR}', echo=False)


async def ensure_db_initialized():
    async with engine.begin() as conn:
        exists = await conn.run_sync(check_table_exists, "authors")
        
        if not exists:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("База данных инициализирована")
        else:
            logger.debug("База данных уже существует")


def check_table_exists(sync_conn, table_name):
    """Синхронная функция-хелпер для проверки существования таблицы."""
    inspector = inspect(sync_conn)
    return inspector.has_table(table_name)


@asynccontextmanager
async def get_db():
    async with AsyncSession(engine) as session:
        yield session
