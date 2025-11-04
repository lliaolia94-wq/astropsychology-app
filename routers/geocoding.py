"""
Роутер для геокодирования: поиск городов и ручной ввод координат.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from database.models import User
from schemas.schemas import (
    ManualCoordinatesRequest,
    GeocodingSearchRequest,
    GeocodingSearchResponse,
    GeocodingErrorResponse,
    UserResponse
)
from services.geocoding_service import geocoding_service
from services.natal_chart_service import natal_chart_service
from routers.auth import get_current_user

router = APIRouter(tags=["Geocoding"], prefix="/api/geocoding")


@router.post(
    "/search",
    response_model=GeocodingSearchResponse,
    summary="Поиск городов в базе данных"
)
async def search_cities(
    request: GeocodingSearchRequest
):
    """
    Поиск городов по запросу для автодополнения в интерфейсе.
    
    Возвращает список городов, соответствующих поисковому запросу.
    """
    cities = geocoding_service.search_cities(
        query=request.query,
        country=request.country,
        limit=request.limit
    )
    
    return GeocodingSearchResponse(
        cities=cities,
        total=len(cities)
    )


@router.post(
    "/manual-coordinates",
    response_model=UserResponse,
    summary="Ручной ввод координат места рождения"
)
async def set_manual_coordinates(
    request: ManualCoordinatesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ручной ввод координат места рождения.
    
    Используется, когда город не найден в базе данных.
    Координаты автоматически валидируются:
    - Широта: от -90 до +90 градусов
    - Долгота: от -180 до +180 градусов
    
    После ввода координат автоматически:
    - Определяется временная зона (если не указана)
    - Обновляется профиль пользователя
    - Пересчитывается натальная карта (если все данные заполнены)
    """
    from datetime import date, time
    from datetime import datetime as dt
    
    # Обновляем профиль с координатами
    result = natal_chart_service.update_user_profile_and_calculate(
        user=current_user,
        db=db,
        birth_date=current_user.birth_date_detailed,
        birth_time=current_user.birth_time_detailed,
        birth_location_name=request.birth_location_name or current_user.birth_location_name,
        birth_country=request.birth_country or current_user.birth_country,
        birth_latitude=request.birth_latitude,
        birth_longitude=request.birth_longitude,
        timezone_name=request.timezone_name
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=400,
            detail=result.get('error', 'Ошибка сохранения координат')
        )
    
    db.refresh(current_user)
    return current_user


@router.get(
    "/geocode/{location_name}",
    summary="Геокодирование города"
)
async def geocode_city(
    location_name: str,
    country: str = None
):
    """
    Геокодирование города по названию.
    
    Возвращает координаты и временную зону, если город найден в базе данных.
    Если город не найден, возвращает ошибку с предложением ручного ввода координат.
    """
    # Нормализуем параметры: убираем пробелы и обрабатываем пустые строки
    location_name = location_name.strip() if location_name else ""
    country = country.strip() if country and country.strip() else None
    
    result = geocoding_service.geocode_location(
        location_name=location_name,
        country=country
    )
    
    if result.get('success'):
        return {
            'success': True,
            'data': result['data']
        }
    else:
        # Возвращаем структурированную ошибку
        raise HTTPException(
            status_code=404,
            detail={
                'error': result.get('error', 'Город не найден'),
                'error_code': result.get('error_code', 'CITY_NOT_FOUND'),
                'requires_manual_input': result.get('requires_manual_input', True),
                'suggestions': result.get('suggestions', []),
                'message': f'Город "{location_name}" не найден в базе данных. Пожалуйста, введите координаты вручную через POST /api/geocoding/manual-coordinates'
            }
        )


@router.get(
    "/validate-coordinates",
    summary="Валидация координат"
)
async def validate_coordinates(
    latitude: float,
    longitude: float
):
    """
    Валидация координат без сохранения.
    
    Проверяет, что координаты находятся в допустимых диапазонах:
    - Широта: от -90 до +90 градусов
    - Долгота: от -180 до +180 градусов
    """
    errors = []
    
    if not (-90 <= latitude <= 90):
        errors.append('Широта должна быть в диапазоне от -90 до +90 градусов')
    
    if not (-180 <= longitude <= 180):
        errors.append('Долгота должна быть в диапазоне от -180 до +180 градусов')
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                'valid': False,
                'errors': errors
            }
        )
    
    # Определяем временную зону по координатам
    timezone = geocoding_service.get_timezone_by_coordinates(latitude, longitude)
    
    return {
        'valid': True,
        'latitude': latitude,
        'longitude': longitude,
        'timezone': timezone
    }

