"""
Роутер для работы с натальными картами.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.database.models import User
from app.models.schemas.schemas import (
    NatalChartCalculateRequest,
    NatalChartCalculateResponse,
    NatalChartRecalculateRequest,
    NatalChartResponse,
    AspectResponse,
    AngleResponse
)
from app.services.natal_chart_service import natal_chart_service
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(tags=["Астрологические метрики"], prefix="/api/natal-chart")


@router.post(
    "/calculate/",
    response_model=NatalChartCalculateResponse,
    summary="Рассчитать натальную карту"
)
async def calculate_natal_chart(
    request: Optional[NatalChartCalculateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Основной endpoint для расчета натальной карты.
    Вызывается при сохранении/изменении данных профиля или по запросу пользователя.
    
    Требует, чтобы в профиле пользователя были указаны:
    - Дата рождения (birth_date_detailed)
    - Время рождения (birth_time_detailed)
    - Координаты места рождения (birth_latitude, birth_longitude)
    - Время рождения в UTC (birth_time_utc)
    """
    houses_system = request.houses_system if request else "placidus"
    
    result = natal_chart_service.calculate_and_save_chart(
        user=current_user,
        db=db,
        houses_system=houses_system,
        force_recalculate=False
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=400,
            detail=result.get('error', 'Ошибка расчета карты')
        )
    
    return NatalChartCalculateResponse(
        chart_id=result['chart_id'],
        status="calculated",
        message=result['message'],
        recalculated=result.get('recalculated', False)
    )


@router.get(
    "/",
    response_model=NatalChartResponse,
    summary="Получить натальную карту пользователя"
)
async def get_natal_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение рассчитанной натальной карты пользователя.
    
    Возвращает полную структуру карты:
    - Позиции всех планет (включая Лунные узлы)
    - Аспекты между планетами
    - Куспиды всех 12 домов
    - ASC и MC
    """
    chart_data = natal_chart_service.get_chart_for_user(current_user, db)
    
    if not chart_data:
        raise HTTPException(
            status_code=404,
            detail="Натальная карта не найдена. Пожалуйста, сначала рассчитайте карту."
        )
    
    # Преобразуем данные для ответа
    # Используем простые словари для planets и houses, так как они уже в нужном формате
    planets_response = {}
    for planet_name, planet_data in chart_data['planets'].items():
        longitude = planet_data['longitude']
        # Вычисляем градусы внутри знака, если их нет
        degree_in_sign = planet_data.get('degree_in_sign', round(longitude % 30, 2))
        planets_response[planet_name] = {
            'planet_name': planet_name,
            'longitude': longitude,
            'zodiac_sign': planet_data['zodiac_sign'],
            'degree_in_sign': degree_in_sign,
            'house': planet_data['house'],
            'is_retrograde': planet_data.get('is_retrograde', False)
        }
    
    aspects_response = []
    for aspect_data in chart_data['aspects']:
        aspects_response.append(AspectResponse(**aspect_data))
    
    houses_response = {}
    for house_num, house_data in chart_data['houses'].items():
        longitude = house_data['longitude']
        # Вычисляем градусы внутри знака, если их нет
        degree_in_sign = house_data.get('degree_in_sign', round(longitude % 30, 2))
        houses_response[str(house_num)] = {
            'house_number': house_num,
            'longitude': longitude,
            'zodiac_sign': house_data['zodiac_sign'],
            'degree_in_sign': degree_in_sign
        }
    
    angles_response = {}
    for angle_name, angle_data in chart_data['angles'].items():
        # Убеждаемся, что degree_in_sign присутствует
        if 'degree_in_sign' not in angle_data:
            longitude = angle_data.get('longitude', 0)
            angle_data['degree_in_sign'] = round(longitude % 30, 2)
        angles_response[angle_name] = AngleResponse(**angle_data)
    
    return NatalChartResponse(
        chart_id=chart_data['chart_id'],
        calculated_at=chart_data['calculated_at'],
        houses_system=chart_data['houses_system'],
        zodiac_type=chart_data['zodiac_type'],
        planets=planets_response,
        aspects=aspects_response,
        houses=houses_response,
        angles=angles_response
    )


@router.post(
    "/recalculate/",
    response_model=NatalChartCalculateResponse,
    summary="Принудительный пересчет натальной карты"
)
async def recalculate_natal_chart(
    request: Optional[NatalChartRecalculateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Принудительный пересчет натальной карты.
    
    Полезно, если:
    - Обновилась логика расчетов
    - Пользователь вручную хочет обновить данные
    - Изменилась система домов
    
    Удаляет старую карту и создает новую.
    """
    houses_system = request.houses_system if request else "placidus"
    
    result = natal_chart_service.calculate_and_save_chart(
        user=current_user,
        db=db,
        houses_system=houses_system,
        force_recalculate=True
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=400,
            detail=result.get('error', 'Ошибка пересчета карты')
        )
    
    return NatalChartCalculateResponse(
        chart_id=result['chart_id'],
        status="recalculated",
        message=result['message'],
        recalculated=True
    )

