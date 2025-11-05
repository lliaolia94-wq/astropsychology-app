"""
Роутер для работы с контекстом общения
Endpoints для управления сессиями, контекстными записями и векторным поиском
"""
import time
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.database.models import User, ContextEntry, ChatSession, ChatMessage
from app.models.schemas.schemas import (
    ContextEntryCreate,
    ContextEntryResponse,
    ContextSaveRequest,
    ContextSaveResponse,
    ContextRelevantRequest,
    ContextRelevantResponse,
    ActiveSessionResponse
)
from app.services.context_service import context_service
from app.services.redis_service import redis_service
from app.workers.context_worker import process_context_save_task, save_context_sync

router = APIRouter(prefix="/api/v1/context", tags=["Context"])


# ============ Управление сессиями ============

@router.get(
    "/sessions/active",
    response_model=ActiveSessionResponse,
    summary="Получить активную сессию пользователя"
)
async def get_active_session(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение активной сессии общения пользователя
    
    Если активной сессии нет или она истекла, создается новая
    """
    session = context_service.get_or_create_active_session(
        db=db,
        user_id=user_id
    )
    
    # Подсчитываем количество сообщений
    message_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_id == session.id
    ).scalar() or 0
    
    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "message_count": message_count,
        "session_type": session.session_type or "regular"
    }


# ============ Асинхронное сохранение контекста ============

@router.post(
    "/async/save",
    response_model=ContextSaveResponse,
    summary="Асинхронное сохранение контекста"
)
async def save_context_async(
    request: ContextSaveRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Асинхронное сохранение контекста в очередь задач
    
    Пользователь получает ответ мгновенно, сохранение происходит в фоне
    """
    # Проверяем существование сессии
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == request.session_id,
            ChatSession.user_id == user_id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    # Пытаемся добавить задачу в очередь Redis
    task_id = redis_service.enqueue_task(
        process_context_save_task,
        session_id=request.session_id,
        user_id=user_id,
        user_message=request.user_message,
        ai_response=request.ai_response,
        trigger_type=request.trigger_type,
        astro_context=request.astro_context
    )
    
    # Если очередь недоступна, выполняем синхронно
    if not task_id:
        # Пробуем синхронное выполнение как fallback
        result = save_context_sync(
            session_id=request.session_id,
            user_id=user_id,
            user_message=request.user_message,
            ai_response=request.ai_response,
            trigger_type=request.trigger_type,
            astro_context=request.astro_context
        )
        return {
            "task_id": "sync",
            "status": "completed" if result.get("success") else "failed",
            "entry_id": result.get("entry_id")
        }
    
    return {
        "task_id": task_id,
        "status": "queued"
    }


@router.get(
    "/async/task/{task_id}",
    summary="Получить статус задачи сохранения"
)
async def get_task_status(task_id: str):
    """
    Получение статуса асинхронной задачи сохранения контекста
    """
    status = redis_service.get_job_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return status


# ============ Семантический поиск ============

@router.post(
    "/async/relevant",
    response_model=ContextRelevantResponse,
    summary="Получить релевантный контекст"
)
async def get_relevant_context(
    request: ContextRelevantRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение релевантного контекста через векторный поиск
    
    Возвращает:
    - 3 последние записи из текущей сессии
    - 5 семантически близких записей из истории
    - Все критически важные записи за 30 дней
    """
    start_time = time.time()
    
    # Проверяем существование сессии
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == request.session_id,
            ChatSession.user_id == user_id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    # Получаем релевантный контекст
    relevant_entries = context_service.get_relevant_context(
        db=db,
        session_id=request.session_id,
        user_id=user_id,
        current_message=request.current_message,
        limit=request.limit
    )
    
    search_time = (time.time() - start_time) * 1000  # в миллисекундах
    
    return {
        "relevant_entries": relevant_entries,
        "search_time": search_time
    }


# ============ Ручное управление контекстом ============

@router.post(
    "/entries/manual",
    response_model=ContextSaveResponse,
    summary="Создать ручную контекстную запись"
)
async def create_manual_entry(
    context_data: ContextEntryCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Создание ручной контекстной записи пользователем
    
    Запись сразу добавляется в очередь для обработки и векторизации
    """
    # Проверяем существование сессии
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == context_data.session_id,
            ChatSession.user_id == user_id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    # Создаем запись синхронно (для ручных записей)
    context_entry = ContextEntry(
        user_id=user_id,
        session_id=context_data.session_id,
        user_message=context_data.user_message,
        ai_response=context_data.ai_response,
        emotional_state=context_data.emotional_state,
        event_description=context_data.event_description,
        insight_text=context_data.insight_text,
        astro_context=context_data.astro_context,
        successful_strategy=context_data.successful_strategy,
        tags=context_data.tags or [],
        priority=context_data.priority,
        entry_type="manual"
    )
    
    db.add(context_entry)
    db.commit()
    db.refresh(context_entry)
    
    # Пытаемся добавить в очередь для векторизации
    if context_entry.user_message or context_entry.ai_response:
        task_id = redis_service.enqueue_task(
            process_context_save_task,
            session_id=context_data.session_id,
            user_id=user_id,
            user_message=context_entry.user_message or "",
            ai_response=context_entry.ai_response or "",
            trigger_type="manual",
            astro_context=context_entry.astro_context
        )
        
        # Если очередь недоступна, выполняем синхронно
        if not task_id:
            result = save_context_sync(
                session_id=context_data.session_id,
                user_id=user_id,
                user_message=context_entry.user_message or "",
                ai_response=context_entry.ai_response or "",
                trigger_type="manual",
                astro_context=context_entry.astro_context
            )
            return {
                "task_id": "sync",
                "status": "completed" if result.get("success") else "failed",
                "entry_id": result.get("entry_id")
            }
        
        return {
            "task_id": task_id,
            "status": "queued"
        }
    
    return {
        "task_id": "sync",
        "status": "completed"
    }


@router.get(
    "/entries",
    response_model=List[ContextEntryResponse],
    summary="Получить список контекстных записей"
)
async def get_context_entries(
    user_id: int,
    session_id: Optional[int] = Query(None, description="Фильтр по сессии"),
    tags: Optional[List[str]] = Query(None, description="Фильтр по тегам"),
    date_from: Optional[datetime] = Query(None, description="Дата начала"),
    date_to: Optional[datetime] = Query(None, description="Дата окончания"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Получение списка контекстных записей с фильтрацией
    
    Поддерживает фильтрацию по:
    - session_id
    - tags
    - date_from / date_to
    """
    query = db.query(ContextEntry).filter(
        ContextEntry.user_id == user_id
    )
    
    if session_id:
        query = query.filter(ContextEntry.session_id == session_id)
    
    if tags:
        # Фильтрация по тегам (простая версия)
        for tag in tags:
            query = query.filter(ContextEntry.tags.contains([tag]))
    
    if date_from:
        query = query.filter(ContextEntry.created_at >= date_from)
    
    if date_to:
        query = query.filter(ContextEntry.created_at <= date_to)
    
    entries = query.order_by(
        ContextEntry.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return entries


@router.put(
    "/entries/{entry_id}",
    response_model=ContextEntryResponse,
    summary="Обновить контекстную запись"
)
async def update_context_entry(
    entry_id: int,
    context_data: ContextEntryCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Обновление контекстной записи
    """
    entry = db.query(ContextEntry).filter(
        and_(
            ContextEntry.id == entry_id,
            ContextEntry.user_id == user_id
        )
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Обновляем поля
    if context_data.emotional_state is not None:
        entry.emotional_state = context_data.emotional_state
    if context_data.event_description is not None:
        entry.event_description = context_data.event_description
    if context_data.insight_text is not None:
        entry.insight_text = context_data.insight_text
    if context_data.tags is not None:
        entry.tags = context_data.tags
    if context_data.priority is not None:
        entry.priority = context_data.priority
    
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    
    return entry


@router.delete(
    "/entries/{entry_id}",
    summary="Удалить контекстную запись"
)
async def delete_context_entry(
    entry_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Удаление контекстной записи
    
    Также удаляет связанный вектор из Qdrant
    """
    entry = db.query(ContextEntry).filter(
        and_(
            ContextEntry.id == entry_id,
            ContextEntry.user_id == user_id
        )
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Удаляем вектор из Qdrant
    if entry.vector_id:
        from app.services.vector_service import vector_service
        vector_service.delete_vector(entry.vector_id)
    
    db.delete(entry)
    db.commit()
    
    return {"message": "Запись удалена"}


# Legacy endpoints (для обратной совместимости)

@router.post(
    "/context",
    response_model=ContextEntryResponse,
    summary="[Legacy] Создать контекстную запись",
    deprecated=True
)
async def create_context_entry_legacy(
    context_data: ContextEntryCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint для создания контекстной записи
    
    Используйте /entries/manual вместо этого
    """
    return await create_manual_entry(context_data, user_id, db)


@router.get(
    "/users/{user_id}/context",
    response_model=List[ContextEntryResponse],
    summary="[Legacy] Список контекстных записей пользователя",
    deprecated=True
)
async def get_user_context_legacy(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint для получения контекстных записей
    
    Используйте /entries вместо этого
    """
    return await get_context_entries(user_id=user_id, db=db)
