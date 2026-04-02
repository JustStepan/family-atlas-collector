from fastapi import Header, HTTPException
from collector.config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")