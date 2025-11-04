from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from database.database import get_db
from database.models import User, ContextEntry
from schemas.schemas import ContextEntryCreate, ContextEntryResponse

router = APIRouter(tags=["Context"])


@router.post("/context", response_model=ContextEntryResponse, summary="Создать контекстную запись")
async def create_context_entry(
        context_data: ContextEntryCreate,
        user_id: int,
        db: Session = Depends(get_db)
):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    db_context = ContextEntry(
        user_id=user_id,
        **context_data.dict()
    )

    db.add(db_context)
    db.commit()
    db.refresh(db_context)

    return db_context


@router.get("/users/{user_id}/context", response_model=List[ContextEntryResponse], summary="Список контекстных записей пользователя")
async def get_user_context(user_id: int, db: Session = Depends(get_db)):
    context_entries = db.scalars(
        select(ContextEntry).where(ContextEntry.user_id == user_id)
        .order_by(ContextEntry.created_at.desc())
    ).all()
    return context_entries

