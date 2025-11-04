from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database.database import get_db
from database.models import User
from schemas.schemas import UserCreate, UserResponse
from routers.auth import get_current_user

router = APIRouter(tags=["Users"])


@router.put("/users/me", response_model=UserResponse, summary="Обновить профиль текущего пользователя")
async def update_current_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление профиля текущего аутентифицированного пользователя
    """
    # Валидация даты и времени, если они предоставлены
    if user_data.birth_date:
        try:
            datetime.strptime(user_data.birth_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД"
            )
    
    if user_data.birth_time:
        try:
            datetime.strptime(user_data.birth_time, "%H:%M")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат времени. Используйте: ЧЧ:ММ"
            )
    
    # Обновление полей
    if user_data.name is not None:
        current_user.name = user_data.name
    if user_data.birth_date is not None:
        current_user.birth_date = user_data.birth_date
    if user_data.birth_time is not None:
        current_user.birth_time = user_data.birth_time
    if user_data.birth_place is not None:
        current_user.birth_place = user_data.birth_place
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/users/me", response_model=UserResponse, summary="Получить профиль текущего пользователя")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Получение профиля текущего аутентифицированного пользователя
    """
    return current_user


@router.get("/users", response_model=List[UserResponse], summary="Список пользователей (только для админов)")
async def get_users(db: Session = Depends(get_db)):
    """
    Получение списка всех пользователей
    TODO: Добавить проверку прав администратора
    """
    users = db.query(User).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse, summary="Получить пользователя по ID")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Получение пользователя по ID
    TODO: Добавить проверку прав доступа
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

