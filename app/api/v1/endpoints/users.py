from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.models.database.models import User
from app.models.schemas.schemas import UserCreate, UserResponse, UserProfileUpdate
from app.api.v1.endpoints.auth import get_current_user
from app.services.natal_chart_service import natal_chart_service
from app.services.geocoding_service import geocoding_service

router = APIRouter(tags=["Пользователь"])


@router.put("/users/me", response_model=UserResponse, summary="Обновить профиль текущего пользователя")
async def update_current_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление профиля текущего аутентифицированного пользователя.
    
    Поддерживает:
    - Старый формат (birth_place) для обратной совместимости
    - Новый формат (birth_location_name, birth_country) с автоматическим геокодированием
    - Ручное указание координат (birth_latitude, birth_longitude)
    
    Автоматически:
    - Геокодирует место рождения, если указаны birth_location_name и birth_country
    - Сохраняет координаты и временную зону
    - Рассчитывает UTC время рождения
    """
    # Обновление имени
    if user_data.name is not None:
        current_user.name = user_data.name
    
    # Обновление текущего местоположения с автоматическим геокодированием
    if user_data.current_location_name is not None:
        current_user.current_location_name = user_data.current_location_name
        
        # Автоматическое геокодирование, если координаты не указаны
        if (user_data.current_latitude is None or user_data.current_longitude is None):
            geo_result = geocoding_service.geocode_location(
                user_data.current_location_name,
                user_data.current_country
            )
            
            if geo_result.get('success'):
                # Город найден в БД
                city_data = geo_result['data']
                current_user.current_latitude = city_data['lat']
                current_user.current_longitude = city_data['lon']
                if not user_data.current_timezone_name and city_data.get('timezone'):
                    current_user.current_timezone_name = city_data['timezone']
            else:
                # Если геокодирование не удалось, но координаты указаны вручную - используем их
                if user_data.current_latitude is not None and user_data.current_longitude is not None:
                    current_user.current_latitude = user_data.current_latitude
                    current_user.current_longitude = user_data.current_longitude
                # Если координаты не найдены и не указаны вручную - просто сохраняем название
                # (не возвращаем ошибку, чтобы не ломать работу старого API)
        
        if user_data.current_country is not None:
            current_user.current_country = user_data.current_country
        if user_data.current_latitude is not None:
            current_user.current_latitude = user_data.current_latitude
        if user_data.current_longitude is not None:
            current_user.current_longitude = user_data.current_longitude
        if user_data.current_timezone_name is not None:
            current_user.current_timezone_name = user_data.current_timezone_name
        elif current_user.current_latitude and current_user.current_longitude and not current_user.current_timezone_name:
            # Определяем временную зону по координатам (только если не указана)
            tz = geocoding_service.get_timezone_by_coordinates(
                float(current_user.current_latitude),
                float(current_user.current_longitude)
            )
            if tz:
                current_user.current_timezone_name = tz
    
    # Обновление старых полей для обратной совместимости
    if user_data.birth_date is not None:
        # Валидация даты
        try:
            datetime.strptime(user_data.birth_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД"
            )
        current_user.birth_date = user_data.birth_date
    
    if user_data.birth_time is not None:
        # Валидация времени
        try:
            datetime.strptime(user_data.birth_time, "%H:%M")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат времени. Используйте: ЧЧ:ММ"
            )
        current_user.birth_time = user_data.birth_time
    
    if user_data.birth_place is not None:
        current_user.birth_place = user_data.birth_place
    
    # Если указаны новые поля (birth_location_name или birth_country), используем расширенное обновление
    if user_data.birth_location_name or user_data.birth_country or user_data.birth_latitude is not None or user_data.birth_longitude is not None:
        # Парсим дату и время для расширенного профиля
        birth_date_obj = None
        birth_time_obj = None
        
        if user_data.birth_date:
            try:
                birth_date_obj = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД"
                )
        
        if user_data.birth_time:
            try:
                birth_time_obj = datetime.strptime(user_data.birth_time, "%H:%M").time()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Неверный формат времени. Используйте: ЧЧ:ММ"
                )
        
        # Обновляем birth_place из новых полей, если они указаны (до вызова сервиса)
        if user_data.birth_location_name and user_data.birth_country:
            # Формируем строку для birth_place из новых полей
            if not user_data.birth_place:  # Если birth_place не указан явно
                current_user.birth_place = f"{user_data.birth_location_name}, {user_data.birth_country}"
        elif user_data.birth_location_name:
            # Если указан только город
            if not user_data.birth_place:
                current_user.birth_place = user_data.birth_location_name
        
        # Используем сервис для расширенного обновления с геокодированием
        result = natal_chart_service.update_user_profile_and_calculate(
            user=current_user,
            db=db,
            birth_date=birth_date_obj,
            birth_time=birth_time_obj,
            birth_location_name=user_data.birth_location_name,
            birth_country=user_data.birth_country,
            birth_latitude=user_data.birth_latitude,
            birth_longitude=user_data.birth_longitude,
            timezone_name=user_data.timezone_name,
            birth_time_utc_offset=user_data.birth_time_utc_offset
        )
        
        if not result['success']:
            # Если ошибка геокодирования, проверяем, нужно ли вернуть ошибку
            # Если указаны только birth_location_name без координат, возвращаем ошибку
            if user_data.birth_location_name and (user_data.birth_latitude is None and user_data.birth_longitude is None):
                # Всегда возвращаем ошибку, если город не найден и координаты не указаны
                # (сервис всегда возвращает requires_manual_input=True при ошибке геокодирования)
                raise HTTPException(
                    status_code=400,
                    detail={
                        'error': result.get('error', 'Город не найден'),
                        'error_code': result.get('error_code', 'CITY_NOT_FOUND'),
                        'requires_manual_input': result.get('requires_manual_input', True),
                        'suggestions': result.get('suggestions', []),
                        'message': result.get('message', f'Не удалось найти координаты для "{user_data.birth_location_name}". Пожалуйста, укажите координаты вручную.')
                    }
                )
            else:
                # Если координаты указаны вручную, но есть другая ошибка - просто сохраняем
                if user_data.birth_place and not current_user.birth_place:
                    current_user.birth_place = user_data.birth_place
                db.commit()
                db.refresh(current_user)
        else:
            # Успешное обновление - сервис уже сделал commit, но обновляем объект
            db.refresh(current_user)
    else:
        # Только старые поля - просто сохраняем
        db.commit()
    
    db.refresh(current_user)
    return current_user


@router.patch("/users/me/profile", response_model=UserResponse, summary="Обновить расширенный профиль пользователя")
async def update_user_profile(
    user_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление расширенного профиля пользователя с данными для расчета натальной карты.
    
    Автоматически:
    - Геокодирует место рождения, если указан birth_location_name (координаты не обязательны)
    - Геокодирует текущее местоположение, если указан current_location_name (координаты не обязательны)
    - Рассчитывает UTC время рождения
    - Пересчитывает натальную карту при обновлении данных
    """
    # Парсим дату и время
    birth_date_obj = None
    birth_time_obj = None
    
    if user_data.birth_date:
        try:
            birth_date_obj = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты. Используйте: ГГГГ-ММ-ДД"
            )
    
    if user_data.birth_time:
        try:
            birth_time_obj = datetime.strptime(user_data.birth_time, "%H:%M").time()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат времени. Используйте: ЧЧ:ММ"
            )
    
    # Обработка текущего местоположения с автоматическим геокодированием
    if user_data.current_location_name is not None:
        current_user.current_location_name = user_data.current_location_name
        
        # Автоматическое геокодирование, если координаты не указаны
        if (user_data.current_latitude is None or user_data.current_longitude is None):
            geo_result = geocoding_service.geocode_location(
                user_data.current_location_name,
                user_data.current_country
            )
            
            if geo_result.get('success'):
                # Город найден в БД
                city_data = geo_result['data']
                current_user.current_latitude = city_data['lat']
                current_user.current_longitude = city_data['lon']
                if not user_data.current_timezone_name and city_data.get('timezone'):
                    current_user.current_timezone_name = city_data['timezone']
            else:
                # Если геокодирование не удалось, но координаты указаны вручную - используем их
                if user_data.current_latitude is not None and user_data.current_longitude is not None:
                    current_user.current_latitude = user_data.current_latitude
                    current_user.current_longitude = user_data.current_longitude
                else:
                    # Если координаты не найдены и не указаны вручную - возвращаем ошибку
                    raise HTTPException(
                        status_code=400,
                        detail={
                            'error': geo_result.get('error', 'Город не найден'),
                            'error_code': geo_result.get('error_code', 'CITY_NOT_FOUND'),
                            'requires_manual_input': geo_result.get('requires_manual_input', True),
                            'suggestions': geo_result.get('suggestions', []),
                            'message': f'Не удалось найти координаты для "{user_data.current_location_name}". Пожалуйста, укажите координаты вручную.'
                        }
                    )
        else:
            # Используем предоставленные координаты
            current_user.current_latitude = user_data.current_latitude
            current_user.current_longitude = user_data.current_longitude
        
        # Обновляем страну и временную зону, если указаны
        if user_data.current_country is not None:
            current_user.current_country = user_data.current_country
        
        if user_data.current_timezone_name is not None:
            current_user.current_timezone_name = user_data.current_timezone_name
        elif current_user.current_latitude and current_user.current_longitude and not current_user.current_timezone_name:
            # Определяем временную зону по координатам (только если не указана)
            tz = geocoding_service.get_timezone_by_coordinates(
                float(current_user.current_latitude),
                float(current_user.current_longitude)
            )
            if tz:
                current_user.current_timezone_name = tz
    
    # Используем сервис для обновления профиля и автоматического пересчета карты
    result = natal_chart_service.update_user_profile_and_calculate(
        user=current_user,
        db=db,
        birth_date=birth_date_obj,
        birth_time=birth_time_obj,
        birth_location_name=user_data.birth_location_name,
        birth_country=user_data.birth_country,
        birth_latitude=user_data.birth_latitude,
        birth_longitude=user_data.birth_longitude,
        timezone_name=user_data.timezone_name,
        birth_time_utc_offset=user_data.birth_time_utc_offset
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=400,
            detail=result.get('error', 'Ошибка обновления профиля')
        )
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users/me", response_model=UserResponse, summary="Получить профиль текущего пользователя")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Получение профиля текущего аутентифицированного пользователя
    """
    return current_user


@router.get("/users", response_model=List[UserResponse], summary="Список пользователей (только для админов)")
async def get_users(db: Session = Depends(get_db)):
    """
    Получение списка всех пользователей
    TODO: Добавить проверку прав администратора
    """
    # Фильтруем пользователей без phone, так как phone обязателен
    users = db.query(User).filter(User.phone.isnot(None)).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse, summary="Получить пользователя по ID")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Получение пользователя по ID
    TODO: Добавить проверку прав доступа
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.phone is None:
        raise HTTPException(status_code=400, detail="У пользователя не указан номер телефона")
    return user

