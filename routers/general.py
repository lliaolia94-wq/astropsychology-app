from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from database.database import get_db

router = APIRouter(tags=["General"])


@router.get("/", summary="Проверка работы API", description="Простой ответ для проверки, что сервис запущен")
async def root():
    return {"message": "Astropsychology API работает в PyCharm!", "status": "OK"}


@router.get("/health", summary="Проверка состояния сервиса и БД")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc)
    }

