from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.database.models import User
from app.services.natal_chart_service import natal_chart_service
from app.services.astro_service import astro_service

router = APIRouter(tags=["Астрологические метрики"], prefix="/api")


@router.post("/calculate-full-chart/{user_id}", summary="Рассчитать натальную карту и сохранить")
async def calculate_full_chart(user_id: int, db: Session = Depends(get_db)):
    """
    Рассчитывает натальную карту для пользователя.
    
    Требует, чтобы в профиле пользователя были указаны:
    - Дата рождения (birth_date_detailed)
    - Время рождения (birth_time_detailed)
    - Координаты места рождения (birth_latitude, birth_longitude)
    - Время рождения в UTC (birth_time_utc)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем наличие необходимых данных
    if not user.birth_date_detailed or not user.birth_time_detailed:
        raise HTTPException(
            status_code=400,
            detail="Не указаны дата или время рождения. Обновите профиль пользователя."
        )
    
    if not user.birth_latitude or not user.birth_longitude:
        raise HTTPException(
            status_code=400,
            detail="Не указаны координаты места рождения. Обновите профиль пользователя с указанием места рождения."
        )
    
    if not user.birth_time_utc:
        raise HTTPException(
            status_code=400,
            detail="Не рассчитано UTC время рождения. Обновите профиль пользователя."
        )
    
    # Используем сервис для расчета карты
    result = natal_chart_service.calculate_and_save_chart(
        user=user,
        db=db,
        houses_system='placidus',
        force_recalculate=True
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка расчета натальной карты: {result.get('error', 'Неизвестная ошибка')}"
        )
    
    # Получаем данные карты для ответа
    chart_data = natal_chart_service.get_chart_for_user(user, db)
    
    if not chart_data:
        raise HTTPException(
            status_code=500,
            detail="Не удалось получить данные рассчитанной карты"
        )
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "chart_id": result['chart_id'],
        "main_signs": {
            "sun": chart_data['planets']['sun']['zodiac_sign'],
            "moon": chart_data['planets']['moon']['zodiac_sign'],
            "ascendant": chart_data['angles']['ascendant']['zodiac_sign']
        },
        "recalculated": result.get('recalculated', False),
        "message": result.get('message', 'Карта успешно рассчитана')
    }



