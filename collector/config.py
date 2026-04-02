from pathlib import Path
from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    BOT_TOKEN: str
    FAMILY_CHAT_IDS: Dict[int, str]
    MSG_TYPES: list[str] = ["voice", "text", "photo", 'document', 'video']
    MSG_SESSION_THRESHOLD: dict[str, int] = {"notes": 5, "diary": 10}

settings = Settings()