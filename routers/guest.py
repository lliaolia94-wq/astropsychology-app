"""
Роутер для гостевых расчетов (без регистрации).
Позволяет рассчитать натальную карту и получить AI-интерпретацию без создания аккаунта.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel

from services.astro_service import astro_service
from services.geocoding_service import geocoding_service
from services.ai_service import ai_service


router = APIRouter(tags=["Guest"], prefix="/api/guest")


class GuestChartRequest(BaseModel):
    """Запрос на расчет карты для гостя"""
    name: Optional[str] = "Гость"
    birth_date: str  # Формат: "1990-10-17"
    birth_time: str  # Формат: "14:30"
    birth_place: str  # Название города
    birth_country: Optional[str] = None
    houses_system: Optional[str] = "placidus"


class GuestChartResponse(BaseModel):
    """Ответ с рассчитанной картой"""
    success: bool
    chart_data: Optional[dict] = None
    main_signs: Optional[dict] = None
    error: Optional[str] = None


class GuestAIRequest(BaseModel):
    """Запрос на AI-интерпретацию для гостя"""
    chart_data: dict  # Данные карты из calculate
    question: Optional[str] = None
    template_type: Optional[str] = "natal_analysis"


@router.post(
    "/calculate-chart",
    response_model=GuestChartResponse,
    summary="Рассчитать натальную карту (гостевой режим)"
)
async def calculate_guest_chart(request: GuestChartRequest):
    """
    Рассчитывает натальную карту без регистрации.
    Не сохраняет данные в БД, только возвращает результат расчета.
    """
    try:
        # Парсим дату и время
        try:
            birth_date_obj = datetime.strptime(request.birth_date, "%Y-%m-%d").date()
        except ValueError:
            try:
                birth_date_obj = datetime.strptime(request.birth_date, "%d.%m.%Y").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD или DD.MM.YYYY")
        
        try:
            birth_time_obj = datetime.strptime(request.birth_time, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат времени. Используйте HH:MM")
        
        # Геокодирование места рождения
        geo_result = geocoding_service.geocode_location(
            request.birth_place,
            request.birth_country
        )
        
        if not geo_result.get('success'):
            raise HTTPException(
                status_code=404,
                detail=f"Город '{request.birth_place}' не найден. Пожалуйста, укажите более точное название."
            )
        
        city_data = geo_result['data']
        latitude = float(city_data['lat'])
        longitude = float(city_data['lon'])
        timezone_name = city_data.get('timezone', 'UTC')
        
        # Рассчитываем UTC время
        birth_time_utc = geocoding_service.calculate_utc_time(
            birth_date_obj,
            birth_time_obj,
            timezone_name
        )
        
        # Рассчитываем натальную карту
        chart_result = astro_service.calculate_natal_chart(
            birth_date=birth_date_obj,
            birth_time_utc=birth_time_utc,
            latitude=latitude,
            longitude=longitude,
            houses_system=request.houses_system or "placidus"
        )
        
        if not chart_result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=chart_result.get('error', 'Ошибка расчета карты')
            )
        
        # Формируем ответ
        planets = chart_result.get('planets', {})
        main_signs = {
            'sun': planets.get('sun', {}).get('zodiac_sign', 'не рассчитан'),
            'moon': planets.get('moon', {}).get('zodiac_sign', 'не рассчитан'),
            'ascendant': chart_result.get('angles', {}).get('ascendant', {}).get('zodiac_sign', 'не рассчитан')
        }
        
        return GuestChartResponse(
            success=True,
            chart_data=chart_result,
            main_signs=main_signs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return GuestChartResponse(
            success=False,
            error=f"Ошибка расчета: {str(e)}"
        )


@router.post(
    "/ai-interpretation",
    summary="Получить AI-интерпретацию карты (гостевой режим)"
)
async def get_guest_ai_interpretation(request: GuestAIRequest):
    """
    Получает AI-интерпретацию натальной карты без регистрации.
    Использует данные карты из calculate-chart.
    """
    try:
        chart_data = request.chart_data
        
        # Извлекаем данные для AI
        planets = chart_data.get('planets', {})
        user_data = {
            'name': 'Гость',
            'sun_sign': planets.get('sun', {}).get('zodiac_sign', 'не рассчитан'),
            'moon_sign': planets.get('moon', {}).get('zodiac_sign', 'не рассчитан'),
            'ascendant_sign': chart_data.get('angles', {}).get('ascendant', {}).get('zodiac_sign', 'не рассчитан')
        }
        
        # Формируем вопрос для AI
        if request.question:
            user_message = request.question
        else:
            user_message = "Расскажи мне о моей натальной карте. Что ты видишь в ней важного?"
        
        # Генерируем ответ через AI
        ai_response = await ai_service.generate_response(
            user_message=user_message,
            user_data=user_data,
            template_type=request.template_type or "natal_analysis",
            context_entries=None,
            mentioned_contacts=None
        )
        
        return {
            "success": True,
            "interpretation": ai_response,
            "template_type": request.template_type or "natal_analysis"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации интерпретации: {str(e)}"
        )

