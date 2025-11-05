"""
Сервис для расчета и сохранения натальных карт в базу данных.
"""
from datetime import datetime, date, time
from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.models.database.models import User, NatalChart, PlanetPosition, Aspect, HouseCuspid
from app.services.astro_service import astro_service
from app.services.geocoding_service import geocoding_service
from app.services.cache_service import natal_chart_cache


class NatalChartService:
    def __init__(self):
        self.astro_service = astro_service
        self.geocoding_service = geocoding_service

    def calculate_and_save_chart(
        self,
        user: User,
        db: Session,
        houses_system: str = 'placidus',
        force_recalculate: bool = False
    ) -> Dict:
        """
        Рассчитывает и сохраняет натальную карту для пользователя.
        
        Args:
            user: Объект пользователя
            db: Сессия базы данных
            houses_system: Система домов (по умолчанию 'placidus')
            force_recalculate: Принудительный пересчет даже если карта уже существует
            
        Returns:
            Dict с результатом расчета
        """
        # Проверяем, есть ли уже карта
        existing_chart = db.query(NatalChart).filter(
            NatalChart.user_profile_id == user.id
        ).first()
        
        if existing_chart and not force_recalculate:
            # Возвращаем существующую карту
            return {
                'success': True,
                'chart_id': existing_chart.id,
                'message': 'Карта уже существует',
                'recalculated': False
            }
        
        # Проверяем наличие необходимых данных
        if not user.birth_date_detailed or not user.birth_time_detailed:
            return {
                'success': False,
                'error': 'Не указаны дата и время рождения'
            }
        
        if not user.birth_latitude or not user.birth_longitude:
            return {
                'success': False,
                'error': 'Не указаны координаты места рождения'
            }
        
        if not user.birth_time_utc:
            return {
                'success': False,
                'error': 'Не рассчитано время рождения в UTC'
            }
        
        try:
            # Рассчитываем натальную карту
            chart_data = self.astro_service.calculate_natal_chart(
                birth_date=user.birth_date_detailed,
                birth_time_utc=user.birth_time_utc,
                latitude=float(user.birth_latitude),
                longitude=float(user.birth_longitude),
                houses_system=houses_system
            )
            
            if not chart_data.get('success'):
                return {
                    'success': False,
                    'error': chart_data.get('error', 'Ошибка расчета карты')
                }
            
            # Удаляем старую карту, если она существует
            if existing_chart:
                db.delete(existing_chart)
                db.flush()  # Применяем удаление перед созданием новой записи
            
            # Создаем новую запись натальной карты
            natal_chart = NatalChart(
                user_profile_id=user.id,
                calculated_at=datetime.now(),
                houses_system=houses_system,
                zodiac_type=chart_data['metadata'].get('zodiac_type', 'tropical')
            )
            db.add(natal_chart)
            db.flush()  # Получаем ID карты
            
            # Сохраняем позиции планет
            planets_data = chart_data.get('planets', {})
            for planet_name, planet_info in planets_data.items():
                planet_position = PlanetPosition(
                    natal_chart_id=natal_chart.id,
                    planet_name=planet_name,
                    longitude=planet_info['longitude'],
                    zodiac_sign=planet_info['zodiac_sign'],
                    house=planet_info.get('house', 1),
                    is_retrograde=1 if planet_info.get('is_retrograde', False) else 0
                )
                db.add(planet_position)
            
            # Сохраняем аспекты
            aspects_data = chart_data.get('aspects', [])
            for aspect_info in aspects_data:
                aspect = Aspect(
                    natal_chart_id=natal_chart.id,
                    planet_1_name=aspect_info['planet_1_name'],
                    planet_2_name=aspect_info['planet_2_name'],
                    aspect_type=aspect_info['aspect_type'],
                    angle=aspect_info['angle'],
                    orb=aspect_info['orb']
                )
                db.add(aspect)
            
            # Сохраняем куспиды домов
            houses_data = chart_data.get('houses', {})
            for house_number, house_info in houses_data.items():
                house_cuspid = HouseCuspid(
                    natal_chart_id=natal_chart.id,
                    house_number=house_number,
                    longitude=house_info['longitude'],
                    zodiac_sign=house_info['zodiac_sign']
                )
                db.add(house_cuspid)
            
            db.commit()
            db.refresh(natal_chart)
            
            # Инвалидируем кеш для пользователя после пересчета
            natal_chart_cache.invalidate(user.id)
            
            return {
                'success': True,
                'chart_id': natal_chart.id,
                'message': 'Карта успешно рассчитана и сохранена',
                'recalculated': existing_chart is not None
            }
            
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'error': f'Ошибка при сохранении карты: {str(e)}'
            }

    def get_chart_for_user(self, user: User, db: Session, use_cache: bool = True) -> Optional[Dict]:
        """
        Получает натальную карту пользователя из базы данных.
        Использует кеш для ускорения доступа.
        
        Args:
            user: Объект пользователя
            db: Сессия базы данных
            use_cache: Использовать кеш (по умолчанию True)
            
        Returns:
            Dict с данными карты или None
        """
        # Проверяем кеш
        if use_cache:
            # Сначала получаем время расчета карты для проверки актуальности
            chart_meta = db.query(NatalChart).filter(
                NatalChart.user_profile_id == user.id
            ).with_entities(NatalChart.calculated_at).first()
            
            if chart_meta:
                cached_data = natal_chart_cache.get(user.id, chart_meta.calculated_at)
                if cached_data is not None:
                    return cached_data
        
        # Если кеша нет или он неактуален, загружаем из БД
        natal_chart = db.query(NatalChart).filter(
            NatalChart.user_profile_id == user.id
        ).first()
        
        if not natal_chart:
            return None
        
        # Собираем данные из связанных таблиц
        planets = {}
        for planet_pos in natal_chart.planet_positions:
            longitude = float(planet_pos.longitude)
            # Вычисляем градусы внутри знака (0-29.99)
            degree_in_sign = round(longitude % 30, 2)
            planets[planet_pos.planet_name] = {
                'longitude': longitude,
                'zodiac_sign': planet_pos.zodiac_sign,
                'degree_in_sign': degree_in_sign,
                'house': planet_pos.house,
                'is_retrograde': bool(planet_pos.is_retrograde)
            }
        
        aspects = []
        for aspect in natal_chart.aspects:
            aspects.append({
                'planet_1_name': aspect.planet_1_name,
                'planet_2_name': aspect.planet_2_name,
                'aspect_type': aspect.aspect_type,
                'angle': float(aspect.angle),
                'orb': float(aspect.orb)
            })
        
        houses = {}
        for house_cuspid in natal_chart.house_cuspids:
            longitude = float(house_cuspid.longitude)
            # Вычисляем градусы внутри знака (0-29.99)
            degree_in_sign = round(longitude % 30, 2)
            houses[house_cuspid.house_number] = {
                'longitude': longitude,
                'zodiac_sign': house_cuspid.zodiac_sign,
                'degree_in_sign': degree_in_sign
            }
        
        # Получаем ASC и MC из домов
        ascendant = houses.get(1, {})
        midheaven = houses.get(10, {})
        
        result = {
            'chart_id': natal_chart.id,
            'calculated_at': natal_chart.calculated_at.isoformat(),
            'houses_system': natal_chart.houses_system,
            'zodiac_type': natal_chart.zodiac_type,
            'planets': planets,
            'aspects': aspects,
            'houses': houses,
            'angles': {
                'ascendant': {
                    'longitude': ascendant.get('longitude', 0),
                    'zodiac_sign': ascendant.get('zodiac_sign', ''),
                    'degree_in_sign': ascendant.get('degree_in_sign', 0)
                },
                'midheaven': {
                    'longitude': midheaven.get('longitude', 0),
                    'zodiac_sign': midheaven.get('zodiac_sign', ''),
                    'degree_in_sign': midheaven.get('degree_in_sign', 0)
                }
            }
        }
        
        # Сохраняем в кеш
        if use_cache:
            natal_chart_cache.set(user.id, result, natal_chart.calculated_at)
        
        return result

    def update_user_profile_and_calculate(
        self,
        user: User,
        db: Session,
        birth_date: Optional[date] = None,
        birth_time: Optional[time] = None,
        birth_location_name: Optional[str] = None,
        birth_country: Optional[str] = None,
        birth_latitude: Optional[float] = None,
        birth_longitude: Optional[float] = None,
        timezone_name: Optional[str] = None,
        birth_time_utc_offset: Optional[float] = None
    ) -> Dict:
        """
        Обновляет профиль пользователя и автоматически пересчитывает карту.
        
        Args:
            user: Объект пользователя
            db: Сессия базы данных
            birth_date: Дата рождения
            birth_time: Время рождения (локальное)
            birth_location_name: Название места рождения
            birth_country: Страна
            birth_latitude: Широта (если известна)
            birth_longitude: Долгота (если известна)
            timezone_name: Название временной зоны
            
        Returns:
            Dict с результатом обновления
        """
        try:
            # Обновляем поля профиля
            if birth_date is not None:
                user.birth_date_detailed = birth_date
            if birth_time is not None:
                user.birth_time_detailed = birth_time
            if birth_location_name is not None:
                user.birth_location_name = birth_location_name
            if birth_country is not None:
                user.birth_country = birth_country
            
            # Геокодирование, если координаты не указаны
            if (birth_latitude is None or birth_longitude is None) and birth_location_name:
                geo_result = self.geocoding_service.geocode_location(
                    birth_location_name,
                    birth_country
                )
                
                if geo_result.get('success'):
                    # Город найден в БД
                    city_data = geo_result['data']
                    user.birth_latitude = city_data['lat']
                    user.birth_longitude = city_data['lon']
                    if not timezone_name and city_data.get('timezone'):
                        timezone_name = city_data['timezone']
                else:
                    # Если геокодирование не удалось, возвращаем структурированную ошибку
                    return {
                        'success': False,
                        'error': geo_result.get('error', 'Город не найден'),
                        'error_code': geo_result.get('error_code', 'CITY_NOT_FOUND'),
                        'requires_manual_input': geo_result.get('requires_manual_input', True),
                        'suggestions': geo_result.get('suggestions', []),
                        'message': f'Не удалось найти координаты для "{birth_location_name}". Пожалуйста, укажите координаты вручную через API endpoint /api/geocoding/manual-coordinates.'
                    }
            else:
                # Используем предоставленные координаты
                if birth_latitude is not None:
                    user.birth_latitude = birth_latitude
                if birth_longitude is not None:
                    user.birth_longitude = birth_longitude
            
            # Определяем временную зону
            if timezone_name is not None:
                user.timezone_name = timezone_name
            elif user.birth_latitude and user.birth_longitude and not user.timezone_name:
                # Определяем временную зону по координатам (только если не указана)
                tz = self.geocoding_service.get_timezone_by_coordinates(
                    float(user.birth_latitude),
                    float(user.birth_longitude)
                )
                if tz:
                    user.timezone_name = tz
            
            # Сохраняем UTC offset, если указан
            if birth_time_utc_offset is not None:
                user.birth_time_utc_offset = birth_time_utc_offset
            
            # Рассчитываем UTC время
            if user.birth_date_detailed and user.birth_time_detailed:
                # Используем явный UTC offset, если указан, иначе timezone_name
                utc_offset = float(user.birth_time_utc_offset) if user.birth_time_utc_offset is not None else None
                user.birth_time_utc = self.geocoding_service.calculate_utc_time(
                    user.birth_date_detailed,
                    user.birth_time_detailed,
                    timezone_name=user.timezone_name,
                    utc_offset_hours=utc_offset
                )
            
            db.commit()
            db.refresh(user)
            
            # Проверяем, что все данные есть для расчета карты
            if (user.birth_date_detailed and user.birth_time_detailed and 
                user.birth_latitude and user.birth_longitude and user.birth_time_utc):
                # Автоматически пересчитываем карту
                chart_result = self.calculate_and_save_chart(
                    user,
                    db,
                    force_recalculate=True
                )
                
                # Кеш будет инвалидирован в calculate_and_save_chart
                
                if chart_result['success']:
                    return {
                        'success': True,
                        'message': 'Профиль обновлен, карта пересчитана',
                        'chart_id': chart_result.get('chart_id')
                    }
                else:
                    return {
                        'success': True,
                        'message': 'Профиль обновлен, но не удалось пересчитать карту',
                        'chart_error': chart_result.get('error')
                    }
            else:
                return {
                    'success': True,
                    'message': 'Профиль обновлен. Для расчета карты необходимо указать все данные рождения.'
                }
                
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'error': f'Ошибка при обновлении профиля: {str(e)}'
            }


# Глобальный экземпляр сервиса
natal_chart_service = NatalChartService()

