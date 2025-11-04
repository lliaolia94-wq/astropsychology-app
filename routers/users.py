from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database.database import get_db
from database.models import User
from schemas.schemas import UserCreate, UserResponse

router = APIRouter(tags=["Users"])


@router.post("/users", response_model=UserResponse, summary="Создать пользователя")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        datetime.strptime(user_data.birth_date, "%Y-%m-%d")
        datetime.strptime(user_data.birth_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты или времени. Используйте: ГГГГ-ММ-ДД и ЧЧ:ММ")

    db_user = User(
        name=user_data.name,
        birth_date=user_data.birth_date,
        birth_time=user_data.birth_time,
        birth_place=user_data.birth_place
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/users", response_model=List[UserResponse], summary="Список пользователей")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse, summary="Получить пользователя по ID")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

