from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timezone

from database.database import get_db
from database.models import User, ChatSession, ChatMessage, Contact, ContextEntry
from schemas.schemas import (
    ChatRequest, ChatResponse, ChatSessionResponse, TemplateInfo
)
from services.ai_service import ai_service
from services.context_service import context_service
from services.astro_service import astro_service

router = APIRouter(tags=["AI"], prefix="/ai")


@router.get("/templates", response_model=List[TemplateInfo], summary="Доступные шаблоны ИИ")
async def get_ai_templates():
    templates = ai_service.get_available_templates()
    return templates


@router.post("/chat", response_model=ChatResponse, summary="Отправить сообщение ИИ-астрологу")
async def chat_with_ai(chat_request: ChatRequest, user_id: int, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if chat_request.session_id:
        session = db.scalar(select(ChatSession).where(ChatSession.id == chat_request.session_id))
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="Сессия чата не найдена")
    else:
        session = ChatSession(
            user_id=user_id,
            template_type=chat_request.template_type,
            title=chat_request.message[:50] + "..."
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    mentioned_contacts = []
    if chat_request.mentioned_contacts:
        for alias in chat_request.mentioned_contacts:
            contact = db.scalar(
                select(Contact).where(
                    (Contact.user_id == user_id) &
                    (Contact.aliases.contains([alias]))
                )
            )
            if contact:
                contact_chart = astro_service.calculate_natal_chart(
                    contact.birth_date,
                    contact.birth_time,
                    contact.birth_place
                )

                mentioned_contacts.append({
                    'name': contact.name,
                    'relationship_type': contact.relationship_type,
                    'sun_sign': contact_chart['planets']['sun']['sign'] if contact_chart['success'] else 'не рассчитан',
                    'moon_sign': contact_chart['planets']['moon']['sign'] if contact_chart['success'] else 'не рассчитан'
                })

    context_entries = context_service.get_relevant_context(user_id, db)

    user_data = {
        'name': user.name,
        'sun_sign': 'Лев',
        'moon_sign': 'Скорпион',
        'ascendant_sign': 'Близнецы'
    }

    ai_response = await ai_service.generate_response(
        user_message=chat_request.message,
        user_data=user_data,
        template_type=chat_request.template_type,
        context_entries=context_entries,
        mentioned_contacts=mentioned_contacts
    )

    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=chat_request.message
    )
    db.add(user_message)

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=ai_response
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    context_data = context_service.extract_context_from_message(
        chat_request.message, ai_response
    )
    if context_data:
        context_entry = ContextEntry(
            user_id=user_id,
            **context_data
        )
        db.add(context_entry)
        db.commit()

    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        message_id=assistant_message.id,
        session_id=session.id,
        assistant_response=ai_response,
        timestamp=assistant_message.timestamp
    )


@router.get("/sessions/{user_id}", response_model=List[ChatSessionResponse], summary="Сессии чата пользователя")
async def get_chat_sessions(user_id: int, db: Session = Depends(get_db)):
    sessions = db.scalars(
        select(ChatSession).where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    ).all()

    result = []
    for session in sessions:
        message_count = db.scalar(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
        )
        session_data = ChatSessionResponse.from_orm(session)
        session_data.message_count = message_count
        result.append(session_data)

    return result

