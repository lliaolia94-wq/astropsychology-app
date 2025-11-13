"""
API endpoints для работы с контактами (использует ContactsRegister)
Обратная совместимость со старыми схемами ContactCreate и ContactResponse
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.database.models import User, ContactsRegister
from app.models.schemas.schemas import ContactCreate, ContactResponse
from app.services.registers_service import registers_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Контакты"])


@router.post("/contacts", response_model=ContactResponse, summary="Создать контакт для пользователя")
async def create_contact(contact_data: ContactCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Создание контакта (использует ContactsRegister)
    Обратная совместимость со старой схемой ContactCreate
    """
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Парсим дату и время из строк
        birth_date_obj = None
        birth_time_obj = None
        
        if contact_data.birth_date:
            try:
                birth_date_obj = datetime.strptime(contact_data.birth_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты рождения (используйте YYYY-MM-DD)")
        
        if contact_data.birth_time:
            try:
                birth_time_obj = datetime.strptime(contact_data.birth_time, "%H:%M").time()
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат времени рождения (используйте HH:MM)")

        # Создаем контакт в регистре
        contact = registers_service.create_contact(
            db=db,
            user_id=user_id,
            name=contact_data.name,
            relationship_type=contact_data.relationship_type,
            birth_date=birth_date_obj,
            birth_time=birth_time_obj,
            birth_place=contact_data.birth_place,
            tags=[contact_data.custom_title] if contact_data.custom_title else None
        )

        logger.info(f"Контакт {contact.id} успешно создан для пользователя {user_id}")
        
        # Преобразуем в старый формат для обратной совместимости
        return ContactResponse(
            id=contact.id,
            user_id=contact.user_id,
            name=contact.name,
            relationship_type=contact.relationship_type,
            custom_title=contact_data.custom_title,
            birth_date=contact_data.birth_date,
            birth_time=contact_data.birth_time,
            birth_place=contact.birth_place or "",
            aliases=contact.tags if contact.tags else [],
            created_at=contact.created_at
        )
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Ошибка базы данных при создании контакта: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при создании контакта: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/users/{user_id}/contacts", response_model=List[ContactResponse], summary="Список контактов пользователя")
async def get_user_contacts(user_id: int, db: Session = Depends(get_db)):
    """
    Получение списка контактов пользователя (использует ContactsRegister)
    Обратная совместимость со старой схемой ContactResponse
    """
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Получаем контакты из регистра
    contacts = db.query(ContactsRegister).filter(
        ContactsRegister.user_id == user_id,
        ContactsRegister.is_active == True
    ).all()
    
    # Преобразуем в старый формат для обратной совместимости
    result = []
    for contact in contacts:
        # Форматируем дату и время обратно в строки
        birth_date_str = contact.birth_date.strftime("%Y-%m-%d") if contact.birth_date else ""
        birth_time_str = contact.birth_time.strftime("%H:%M") if contact.birth_time else ""
        
        # Извлекаем custom_title из тегов (первый тег)
        custom_title = contact.tags[0] if contact.tags and len(contact.tags) > 0 else None
        
        result.append(ContactResponse(
            id=contact.id,
            user_id=contact.user_id,
            name=contact.name,
            relationship_type=contact.relationship_type,
            custom_title=custom_title,
            birth_date=birth_date_str,
            birth_time=birth_time_str,
            birth_place=contact.birth_place or "",
            aliases=contact.tags if contact.tags else [],
            created_at=contact.created_at
        ))
    
    return result

