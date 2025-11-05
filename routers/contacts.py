from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import logging

from database.database import get_db
from database.models import User, Contact
from schemas.schemas import ContactCreate, ContactResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contacts"])


@router.post("/contacts", response_model=ContactResponse, summary="Создать контакт для пользователя")
async def create_contact(contact_data: ContactCreate, user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        aliases = []
        if contact_data.custom_title:
            aliases.append(contact_data.custom_title.lower())
        aliases.append(contact_data.name.lower())
        aliases.append(contact_data.relationship_type.lower())

        db_contact = Contact(
            user_id=user_id,
            name=contact_data.name,
            relationship_type=contact_data.relationship_type,
            custom_title=contact_data.custom_title,
            birth_date=contact_data.birth_date,
            birth_time=contact_data.birth_time,
            birth_place=contact_data.birth_place,
            aliases=aliases
        )

        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)

        logger.info(f"Контакт {db_contact.id} успешно создан для пользователя {user_id}")
        return db_contact
    
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
    contacts = db.scalars(select(Contact).where(Contact.user_id == user_id)).all()
    return contacts

