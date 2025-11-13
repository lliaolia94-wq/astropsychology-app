from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.database.models import User, ChatSession, ChatMessage, ContactsRegister
from app.models.schemas.schemas import (
    ChatRequest, ChatResponse, ChatSessionResponse, TemplateInfo
)
from app.services.ai_service import ai_service
from app.services.context_service import context_service
from app.services.astro_service import astro_service
from app.services.redis_service import redis_service
from app.workers.context_worker import process_context_save_task

router = APIRouter(tags=["ИИ и контекст"], prefix="/ai")


@router.get("/templates", response_model=List[TemplateInfo], summary="Доступные шаблоны ИИ")
async def get_ai_templates():
    templates = ai_service.get_available_templates()
    return templates


@router.post("/chat", response_model=ChatResponse, summary="Отправить сообщение ИИ-астрологу")
async def chat_with_ai(chat_request: ChatRequest, user_id: int, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем смену темы (создание новой сессии)
    force_new_session = context_service.check_topic_change(chat_request.message)
    
    # Получаем или создаем активную сессию
    if chat_request.session_id and not force_new_session:
        session = db.scalar(select(ChatSession).where(
            (ChatSession.id == chat_request.session_id) &
            (ChatSession.user_id == user_id)
        ))
        if not session:
            raise HTTPException(status_code=404, detail="Сессия чата не найдена")
        # Проверяем истекла ли сессия
        if context_service.check_session_timeout(db, session.id):
            force_new_session = True
    
    if force_new_session or not chat_request.session_id:
        # Создаем новую сессию
        session = context_service.get_or_create_active_session(
            db=db,
            user_id=user_id,
            template_type=chat_request.template_type,
            force_new=force_new_session
        )
    else:
        # Обновляем время сессии
        session.updated_at = datetime.now(timezone.utc)
        db.commit()

    mentioned_contacts = []
    if chat_request.mentioned_contacts:
        # Получаем все контакты пользователя из регистра для поиска по тегам/имени
        all_contacts = db.query(ContactsRegister).filter(
            ContactsRegister.user_id == user_id,
            ContactsRegister.is_active == True
        ).all()
        
        for alias in chat_request.mentioned_contacts:
            alias_lower = alias.lower()
            contact = None
            
            # Ищем контакт по тегам, имени, relationship_type
            for cont in all_contacts:
                found = False
                
                # Проверяем теги (массив строк в JSON)
                if cont.tags:
                    tags_list = cont.tags if isinstance(cont.tags, list) else []
                    if any(alias_lower in str(t).lower() for t in tags_list):
                        found = True
                
                # Проверяем имя и relationship_type
                if not found:
                    if (cont.name and alias_lower in cont.name.lower()) or \
                       (cont.relationship_type and alias_lower in cont.relationship_type.lower()):
                        found = True
                
                if found:
                    contact = cont
                    break
            
            if contact and contact.birth_date and contact.birth_time and contact.birth_place:
                # Форматируем дату и время для расчета карты
                birth_date_str = contact.birth_date.strftime("%Y-%m-%d")
                birth_time_str = contact.birth_time.strftime("%H:%M")
                
                contact_chart = astro_service.calculate_natal_chart(
                    birth_date_str,
                    birth_time_str,
                    contact.birth_place
                )

                mentioned_contacts.append({
                    'name': contact.name,
                    'relationship_type': contact.relationship_type,
                    'sun_sign': contact_chart['planets']['sun']['sign'] if contact_chart['success'] else 'не рассчитан',
                    'moon_sign': contact_chart['planets']['moon']['sign'] if contact_chart['success'] else 'не рассчитан'
                })

    # Получаем релевантный контекст для промпта
    context_entries = context_service.get_relevant_context(
        db=db,
        session_id=session.id,
        user_id=user_id,
        current_message=chat_request.message,
        limit=10
    )

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

    # Подсчитываем количество сообщений в сессии
    message_count = db.scalar(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
    ) or 0
    
    # Проверяем триггеры сохранения контекста
    should_save, trigger_type = context_service.should_save_context(
        db=db,
        session_id=session.id,
        user_message=chat_request.message,
        message_count=message_count + 2  # +2 потому что мы только что добавили 2 сообщения
    )
    
    # Сохраняем контекст асинхронно если нужно
    if should_save:
        # Получаем астрологический контекст (если нужен)
        astro_context = None  # TODO: Получить актуальный астрологический контекст
        
        # Добавляем задачу в очередь
        task_id = redis_service.enqueue_task(
            process_context_save_task,
            session_id=session.id,
            user_id=user_id,
            user_message=chat_request.message,
            ai_response=ai_response,
            trigger_type=trigger_type,
            astro_context=astro_context
        )
        
        if task_id:
            # Инвалидируем кеш сессии
            redis_service.invalidate_session_context(session.id)

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

