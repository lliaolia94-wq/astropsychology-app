from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json

from database.database import get_db
from database.models import User, NatalChart
from services.astro_service import astro_service

router = APIRouter(tags=["Astrology"], prefix="/api")


@router.post("/calculate-full-chart/{user_id}", summary="Рассчитать натальную карту и сохранить")
async def calculate_full_chart(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    natal_chart = astro_service.calculate_natal_chart(
        user.birth_date,
        user.birth_time,
        user.birth_place
    )

    if not natal_chart['success']:
        raise HTTPException(status_code=500, detail=f"Ошибка расчета: {natal_chart['error']}")

    db_chart = NatalChart(
        user_id=user_id,
        sun_sign=natal_chart['planets']['sun']['sign'],
        moon_sign=natal_chart['planets']['moon']['sign'],
        ascendant_sign=natal_chart['angles']['ascendant']['sign'],
        midheaven_sign=natal_chart['angles']['midheaven']['sign'],
        planets_data=json.dumps(natal_chart['planets']),
        houses_data=json.dumps(natal_chart['houses']),
        angles_data=json.dumps(natal_chart['angles'])
    )

    db.add(db_chart)
    db.commit()
    db.refresh(db_chart)

    return {
        "user_id": user_id,
        "user_name": user.name,
        "chart_id": db_chart.id,
        "main_signs": {
            "sun": natal_chart['planets']['sun']['sign'],
            "moon": natal_chart['planets']['moon']['sign'],
            "ascendant": natal_chart['angles']['ascendant']['sign']
        },
        "calculation_time": natal_chart['metadata']['calculation_time']
    }


@router.get("/professional-calendar/{user_id}/{year}/{month}", summary="Календарь транзитов на месяц")
async def get_professional_calendar(user_id: int, year: int, month: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    natal_chart = astro_service.calculate_natal_chart(
        user.birth_date,
        user.birth_time,
        user.birth_place
    )

    if not natal_chart['success']:
        raise HTTPException(status_code=500, detail=f"Ошибка расчета натальной карты: {natal_chart['error']}")

    calendar = astro_service.generate_calendar_with_transits(natal_chart, year, month)

    return {
        "user_id": user_id,
        "user_name": user.name,
        "calendar": calendar
    }


@router.get("/daily-transits/{user_id}/{date}", summary="Детальные транзиты на день")
async def get_daily_transits(user_id: int, date: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД")

    natal_chart = astro_service.calculate_natal_chart(
        user.birth_date,
        user.birth_time,
        user.birth_place
    )

    if not natal_chart['success']:
        raise HTTPException(status_code=500, detail=f"Ошибка расчета натальной карты: {natal_chart['error']}")

    transits = astro_service.calculate_transits(natal_chart, date)

    if not transits['success']:
        raise HTTPException(status_code=500, detail=f"Ошибка расчета транзитов: {transits['error']}")

    return {
        "user_id": user_id,
        "date": date,
        "transits": transits
    }

