from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from database.database import get_db
from database.models import User, Contact
from schemas.schemas import ContactCreate, ContactResponse

router = APIRouter(tags=["Contacts"])


@router.post("/contacts", response_model=ContactResponse, summary="Создать контакт для пользователя")
async def create_contact(contact_data: ContactCreate, user_id: int, db: Session = Depends(get_db)):
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

    return db_contact


@router.get("/users/{user_id}/contacts", response_model=List[ContactResponse], summary="Список контактов пользователя")
async def get_user_contacts(user_id: int, db: Session = Depends(get_db)):
    contacts = db.scalars(select(Contact).where(Contact.user_id == user_id)).all()
    return contacts

