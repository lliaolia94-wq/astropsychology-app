"""
API endpoints для работы с регистрами контекстной информации
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, date, timedelta, timezone

from app.core.database import get_db
from app.models.database.models import User, EventsRegister, ContactsRegister, TransitsRegister
from app.models.schemas.schemas import (
    EventCreate, EventUpdate, EventResponse,
    ContactRegisterCreate, ContactRegisterUpdate, ContactRegisterResponse,
    TransitCreate, TransitResponse,
    ContextQueryRequest, ContextSliceResponse
)
from app.services.registers_service import registers_service
from app.services.context_query import ContextQuery
from app.services.natal_chart_service import natal_chart_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registers")


# ============ EVENTS ============

@router.post("/events", response_model=EventResponse, summary="Создать событие", tags=["ИИ и контекст"])
async def create_event(
    event_data: EventCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Создание нового события в регистре"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    event = registers_service.create_event(
        db=db,
        user_id=user_id,
        event_type=event_data.event_type,
        category=event_data.category,
        event_date=event_data.event_date,
        effective_from=event_data.effective_from,
        effective_to=event_data.effective_to,
        title=event_data.title,
        description=event_data.description,
        user_message=event_data.user_message,
        ai_response=event_data.ai_response,
        insight_text=event_data.insight_text,
        emotional_state=event_data.emotional_state,
        emotional_intensity=event_data.emotional_intensity,
        emotional_trigger=event_data.emotional_trigger,
        tags=event_data.tags,
        priority=event_data.priority,
        session_id=event_data.session_id,
        contact_ids=event_data.contact_ids
    )
    
    return registers_service._event_to_dict(event)


@router.get("/events/{event_id}", response_model=EventResponse, summary="Получить событие", tags=["ИИ и контекст"])
async def get_event(
    event_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получение события по ID"""
    event = registers_service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    if event.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому событию")
    
    return registers_service._event_to_dict(event)


@router.put("/events/{event_id}", response_model=EventResponse, summary="Обновить событие", tags=["ИИ и контекст"])
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Обновление события"""
    event = registers_service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    if event.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому событию")
    
    update_data = event_data.dict(exclude_unset=True)
    updated_event = registers_service.update_event(db, event_id, **update_data)
    
    if not updated_event:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении события")
    
    return registers_service._event_to_dict(updated_event)


@router.delete("/events/{event_id}", summary="Удалить событие", tags=["ИИ и контекст"])
async def delete_event(
    event_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Удаление события"""
    event = registers_service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    if event.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому событию")
    
    success = registers_service.delete_event(db, event_id)
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при удалении события")
    
    return {"message": "Событие удалено", "event_id": event_id}


# ============ CONTACTS ============

@router.post("/contacts", response_model=ContactRegisterResponse, summary="Создать контакт", tags=["Контакты"])
async def create_contact(
    contact_data: ContactRegisterCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Создание нового контакта в регистре"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Парсим дату и время если указаны
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
    
    contact = registers_service.create_contact(
        db=db,
        user_id=user_id,
        name=contact_data.name,
        relationship_type=contact_data.relationship_type,
        relationship_depth=contact_data.relationship_depth,
        birth_date=birth_date_obj,
        birth_time=birth_time_obj,
        birth_place=contact_data.birth_place,
        timezone=contact_data.timezone,
        interaction_frequency=contact_data.interaction_frequency,
        tags=contact_data.tags,
        privacy_level=contact_data.privacy_level
    )
    
    return registers_service._contact_to_dict(contact)


@router.get("/contacts/{contact_id}", response_model=ContactRegisterResponse, summary="Получить контакт", tags=["Контакты"])
async def get_contact(
    contact_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получение контакта по ID"""
    contact = registers_service.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    if contact.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому контакту")
    
    return registers_service._contact_to_dict(contact)


@router.get("/contacts", response_model=List[ContactRegisterResponse], summary="Список контактов", tags=["Контакты"])
async def list_contacts(
    user_id: int,
    active_only: bool = Query(True, description="Только активные контакты"),
    db: Session = Depends(get_db)
):
    """Получение списка контактов пользователя"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    query = db.query(ContactsRegister).filter(ContactsRegister.user_id == user_id)
    
    if active_only:
        query = query.filter(ContactsRegister.is_active == True)
    
    contacts = query.all()
    
    return [registers_service._contact_to_dict(c) for c in contacts]


@router.put("/contacts/{contact_id}", response_model=ContactRegisterResponse, summary="Обновить контакт", tags=["Контакты"])
async def update_contact(
    contact_id: int,
    contact_data: ContactRegisterUpdate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Обновление контакта"""
    contact = registers_service.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    if contact.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому контакту")
    
    update_data = contact_data.dict(exclude_unset=True)
    updated_contact = registers_service.update_contact(db, contact_id, **update_data)
    
    if not updated_contact:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении контакта")
    
    return registers_service._contact_to_dict(updated_contact)


@router.delete("/contacts/{contact_id}", summary="Удалить контакт", tags=["Контакты"])
async def delete_contact(
    contact_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Удаление контакта (мягкое удаление)"""
    contact = registers_service.get_contact_by_id(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    if contact.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому контакту")
    
    success = registers_service.delete_contact(db, contact_id)
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при удалении контакта")
    
    return {"message": "Контакт удален", "contact_id": contact_id}


# ============ TRANSITS ============

@router.post("/transits", response_model=TransitResponse, summary="Создать транзит", tags=["Астрологические метрики"])
async def create_transit(
    transit_data: TransitCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Создание нового транзита"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Парсим даты
    try:
        start_date = datetime.strptime(transit_data.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(transit_data.end_date, "%Y-%m-%d").date()
        transit_date = datetime.strptime(transit_data.transit_date, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты: {str(e)}")
    
    transit = registers_service.create_transit(
        db=db,
        user_id=user_id,
        transit_type=transit_data.transit_type,
        planet_from=transit_data.planet_from,
        planet_to=transit_data.planet_to,
        start_date=start_date,
        end_date=end_date,
        transit_date=transit_date,
        impact_level=transit_data.impact_level,
        aspect_type=transit_data.aspect_type,
        exact_time=transit_data.exact_time,
        orb=transit_data.orb,
        strength=transit_data.strength,
        house=transit_data.house,
        interpretation=transit_data.interpretation,
        impact_areas=transit_data.impact_areas
    )
    
    return registers_service._transit_to_dict(transit)


@router.get("/transits/{transit_id}", response_model=TransitResponse, summary="Получить транзит", tags=["Астрологические метрики"])
async def get_transit(
    transit_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получение транзита по ID"""
    transit = registers_service.get_transit_by_id(db, transit_id)
    if not transit:
        raise HTTPException(status_code=404, detail="Транзит не найден")
    
    if transit.user_id != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому транзиту")
    
    return registers_service._transit_to_dict(transit)


@router.get("/transits", response_model=List[TransitResponse], summary="Список транзитов", tags=["Астрологические метрики"])
async def list_transits(
    user_id: int,
    start_date: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    impact_level: Optional[str] = Query(None, description="Уровень влияния"),
    db: Session = Depends(get_db)
):
    """Получение списка транзитов пользователя"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    query = db.query(TransitsRegister).filter(TransitsRegister.user_id == user_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(TransitsRegister.start_date >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат start_date")
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(TransitsRegister.end_date <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат end_date")
    
    if impact_level:
        query = query.filter(TransitsRegister.impact_level == impact_level)
    
    transits = query.order_by(TransitsRegister.transit_date).all()
    
    return [registers_service._transit_to_dict(t) for t in transits]


@router.get("/transits/calendar/{user_id}/{year}/{month}", summary="Календарь транзитов на месяц", tags=["Астрологические метрики"])
async def get_professional_calendar(
    user_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    """
    Получение календаря транзитов на месяц из регистра.
    
    Если транзитов нет в регистре, они автоматически рассчитываются и сохраняются.
    """
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем наличие натальной карты
    chart_data = natal_chart_service.get_chart_for_user(user, db)
    if not chart_data:
        raise HTTPException(
            status_code=404,
            detail="Натальная карта не найдена. Сначала рассчитайте карту через /api/calculate-full-chart/{user_id}"
        )
    
    # Получаем календарь из регистра (или рассчитываем)
    calendar = registers_service.get_or_calculate_calendar(
        db=db,
        user=user,
        year=year,
        month=month
    )
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "calendar": calendar
    }


@router.get("/transits/daily/{user_id}/{date}", summary="Детальные транзиты на день", tags=["Астрологические метрики"])
async def get_daily_transits(
    user_id: int,
    date: str,
    db: Session = Depends(get_db)
):
    """
    Получение детальных транзитов на конкретную дату из регистра.
    
    Если транзитов нет в регистре, они автоматически рассчитываются и сохраняются.
    Использует текущее местоположение пользователя или место рождения.
    """
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД")
    
    # Определяем координаты для расчета транзитов
    latitude = None
    longitude = None
    location_name = None
    country = None
    timezone_name = None
    location_type = None
    
    # Проверяем наличие текущего местоположения
    if (user.current_latitude is not None and 
        user.current_longitude is not None and
        float(user.current_latitude) != 0 and 
        float(user.current_longitude) != 0):
        latitude = float(user.current_latitude)
        longitude = float(user.current_longitude)
        location_name = user.current_location_name or "Не указано"
        country = user.current_country or "Не указано"
        timezone_name = user.current_timezone_name
        location_type = "current"
    elif (user.birth_latitude is not None and 
          user.birth_longitude is not None and
          float(user.birth_latitude) != 0 and 
          float(user.birth_longitude) != 0):
        latitude = float(user.birth_latitude)
        longitude = float(user.birth_longitude)
        location_name = user.birth_location_name or "Не указано"
        country = user.birth_country or "Не указано"
        timezone_name = user.timezone_name
        location_type = "birth"
    else:
        raise HTTPException(
            status_code=400,
            detail="Не указано текущее местоположение или место рождения. Обновите профиль пользователя."
        )
    
    # Получаем транзиты из регистра (или рассчитываем)
    try:
        transits_data = registers_service.get_or_calculate_transits_for_date(
            db=db,
            user=user,
            target_date=target_date,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения транзитов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения транзитов: {str(e)}")
    
    return {
        "user_id": user_id,
        "date": date,
        "location": {
            "type": location_type,
            "name": location_name,
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name
        },
        "transits": transits_data
    }


# ============ CONTEXT QUERIES ============

@router.post("/context/query", response_model=ContextSliceResponse, summary="Выполнить контекстный запрос", tags=["ИИ и контекст"])
async def query_context(
    query_request: ContextQueryRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Выполнение параметризованного запроса к регистрам"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Создаем запрос
    query = ContextQuery(user_id=user_id, db=db)
    
    # Устанавливаем временной диапазон
    if query_request.days:
        query.for_days(query_request.days)
    elif query_request.start_date or query_request.end_date:
        query.for_period(
            query_request.start_date or datetime.now(timezone.utc) - timedelta(days=30),
            query_request.end_date or datetime.now(timezone.utc)
        )
    
    # Применяем фильтры
    if query_request.categories:
        query.with_categories(query_request.categories)
    
    if query_request.emotional_states:
        query.with_emotional_state(query_request.emotional_states)
    
    if query_request.tags:
        query.with_tags(query_request.tags)
    
    if query_request.min_priority or query_request.max_priority:
        query.with_priority(query_request.min_priority, query_request.max_priority)
    
    # Включаем связанные данные
    if query_request.include_contacts:
        query.include_contacts()
    
    if query_request.include_transits:
        query.include_transits()
    
    if query_request.include_karmic_themes:
        query.include_karmic_themes()
    
    # Устанавливаем лимит
    if query_request.limit:
        query.set_limit(query_request.limit)
    
    # Выполняем запрос
    result = query.execute()
    
    # Преобразуем в формат ответа
    return ContextSliceResponse(
        events=[EventResponse(**e) for e in result.events],
        contacts=[ContactRegisterResponse(**c) for c in result.contacts] if result.contacts else None,
        transits=[TransitResponse(**t) for t in result.transits] if result.transits else None,
        statistics=result.statistics,
        patterns=result.patterns
    )

