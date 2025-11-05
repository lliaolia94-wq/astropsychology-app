"""
Профессиональный астрологический сервис для расчета натальных карт.
Использует pyswisseph (Swiss Ephemeris) для всех расчетов: планет, домов и аспектов.
"""
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import pytz
import swisseph as swe

# Импортируем конфигурацию
try:
    from config import config as astrology_config
except ImportError:
    # Fallback на значения по умолчанию, если config не найден
    class DefaultConfig:
        DEFAULT_ORBS = {
            'conjunction': 8.0,
            'opposition': 8.0,
            'trine': 8.0,
            'square': 8.0,
            'sextile': 6.0,
        }
        ASPECTS = [
            (0, 'conjunction', 'соединение'),
            (60, 'sextile', 'секстиль'),
            (90, 'square', 'квадрат'),
            (120, 'trine', 'трин'),
            (180, 'opposition', 'оппозиция')
        ]
        def get_orbs(self):
            return self.DEFAULT_ORBS.copy()
    astrology_config = DefaultConfig()


class ProfessionalAstroService:
    def __init__(self):
        # Загружаем орбисы из конфигурации
        self._orbs = astrology_config.get_orbs()
        
        # Аспекты из конфигурации
        self._aspects = astrology_config.ASPECTS
        
        # Знаки зодиака (на русском и английском)
        self.zodiac_signs_ru = [
            "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
            "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
        ]
        self.zodiac_signs_en = [
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
        ]

        # Маппинг планет для pyswisseph
        self.sweph_planets = {
            'sun': swe.SUN,
            'moon': swe.MOON,
            'mercury': swe.MERCURY,
            'venus': swe.VENUS,
            'mars': swe.MARS,
            'jupiter': swe.JUPITER,
            'saturn': swe.SATURN,
            'uranus': swe.URANUS,
            'neptune': swe.NEPTUNE,
            'pluto': swe.PLUTO,
            'true_node': swe.TRUE_NODE,  # Истинный Лунный узел (северный)
        }
        
        # Названия планет на русском (для обратной совместимости)
        self.planet_names_ru = {
            'sun': 'Солнце',
            'moon': 'Луна',
            'mercury': 'Меркурий',
            'venus': 'Венера',
            'mars': 'Марс',
            'jupiter': 'Юпитер',
            'saturn': 'Сатурн',
            'uranus': 'Уран',
            'neptune': 'Нептун',
            'pluto': 'Плутон',
            'true_node': 'Лунный Узел'
        }
        
        print("✅ Swiss Ephemeris инициализирован для всех расчетов")
        print(f"✅ Орбисы аспектов загружены: {self._orbs}")
    
    @property
    def ORBS(self) -> Dict[str, float]:
        """Получить текущие орбисы аспектов"""
        return self._orbs.copy()
    
    @property
    def ASPECTS(self) -> List[Tuple[int, str, str]]:
        """Получить список аспектов"""
        return self._aspects
    
    def get_orb(self, aspect_name: str) -> float:
        """
        Получить орбис для конкретного аспекта.
        
        Args:
            aspect_name: Название аспекта
            
        Returns:
            Орбис в градусах
        """
        return self._orbs.get(aspect_name, 0.0)
    
    def set_orb(self, aspect_name: str, orb_value: float):
        """
        Установить орбис для аспекта (динамически).
        
        Args:
            aspect_name: Название аспекта
            orb_value: Значение орбиса в градусах
        """
        if aspect_name not in self._orbs:
            print(f"⚠️ Предупреждение: аспект '{aspect_name}' не найден в конфигурации")
        self._orbs[aspect_name] = float(orb_value)
    
    def reload_config(self):
        """Перезагрузить конфигурацию (для обновления через переменные окружения)"""
        self._orbs = astrology_config.get_orbs()

    def _degrees_to_zodiac_sign(self, longitude: float) -> Tuple[str, str, float]:
        """
        Преобразует эклиптическую долготу в знак зодиака
        Возвращает (название_знака_ru, название_знака_en, градус_в_знаке)
        """
        sign_num = int(longitude / 30) % 12
        degree_in_sign = longitude % 30
        return (
            self.zodiac_signs_ru[sign_num],
            self.zodiac_signs_en[sign_num],
            degree_in_sign
        )

    def _calculate_planet_position(
        self, 
        planet_key: str, 
        jd: float
    ) -> Optional[Dict]:
        """
        Рассчитывает позицию планеты используя pyswisseph (Swiss Ephemeris).
        
        Args:
            planet_key: Ключ планеты ('sun', 'moon', 'mercury', etc.)
            jd: Юлианская дата
            
        Returns:
            Dict с данными о позиции планеты или None при ошибке
        """
        try:
            if planet_key not in self.sweph_planets:
                return None
            
            planet_id = self.sweph_planets[planet_key]
            
            # Расчет позиции планеты с флагом скорости для определения ретроградности
            # swe.FLG_SWIEPH использует встроенные эфемериды Swiss Ephemeris
            # swe.FLG_SPEED возвращает скорость планеты (необходимо для ретроградности)
            flags = swe.FLG_SWIEPH | swe.FLG_SPEED
            xx, retflag = swe.calc_ut(jd, planet_id, flags)
            
            if retflag < 0:
                print(f"⚠️ Ошибка расчета {planet_key} через Swiss Ephemeris: {retflag}")
                return None
            
            # xx[0] - долгота в градусах (эклиптическая)
            # xx[1] - широта в градусах
            # xx[2] - расстояние (если применимо)
            # xx[3] - скорость по долготе в градусах/день (для определения ретроградности)
            longitude = xx[0]
            if longitude < 0:
                longitude += 360
            
            # Определяем знак зодиака
            sign_ru, sign_en, degree = self._degrees_to_zodiac_sign(longitude)
            
            # Определяем ретроградность по скорости
            # Отрицательная скорость = ретроградность
            is_retrograde = False
            speed_longitude = 0.0
            if len(xx) > 3:
                speed_longitude = xx[3]  # Скорость по долготе в градусах/день
                is_retrograde = speed_longitude < 0
            
            return {
                'longitude': round(longitude, 6),
                'zodiac_sign': sign_en,
                'zodiac_sign_ru': sign_ru,
                'degree_in_sign': round(degree, 2),
                'latitude': round(xx[1], 6) if len(xx) > 1 else 0.0,
                'is_retrograde': is_retrograde,
                'speed': round(speed_longitude, 6)  # Скорость планеты для справки
            }
        except Exception as e:
            print(f"⚠️ Ошибка расчета {planet_key} через Swiss Ephemeris: {e}")
            return None

    def _calculate_houses(
        self, 
        jd: float, 
        lat: float, 
        lon: float, 
        houses_system: str = 'placidus'
    ) -> Dict:
        """
        Рассчитывает куспиды домов используя pyswisseph
        
        Args:
            jd: Юлианская дата
            lat: Широта места рождения
            lon: Долгота места рождения
            houses_system: Система домов ('placidus', 'koch', 'equal', etc.)
            
        Returns:
            Dict с куспидами домов (1-12) и углами (ASC, MC)
        """
        # Маппинг систем домов для Swiss Ephemeris
        house_systems = {
            'placidus': b'P',
            'koch': b'K',
            'equal': b'E',
            'whole': b'W',
            'regiomontanus': b'R',
            'campanus': b'C'
        }
        
        hsys = house_systems.get(houses_system.lower(), b'P')  # По умолчанию Плацидус
        
        try:
            # Преобразуем координаты в float, если они Decimal
            lat = float(lat)
            lon = float(lon)
            
            # Расчет домов
            result = swe.houses(jd, lat, lon, hsys)
            
            # swe.houses может возвращать результат в разных форматах:
            # Старый формат: (cusps, ascmc) - 2 элемента
            # Новый формат: (retval, cusps, ascmc, serr) - 4 элемента
            # Где:
            # retval - код возврата (0 = успех, <0 = ошибка)
            # cusps - массив куспидов (13 элементов: cusps[0] не используется, cusps[1-12] - дома 1-12)
            # ascmc - массив углов (4 элемента: ASC, MC, ARMC, Vertex)
            # serr - строка с ошибкой
            
            if len(result) == 2:
                # Старый формат: (cusps, ascmc)
                cusps, ascmc = result
                retval = 0  # Считаем успешным
                serr = None
            elif len(result) == 4:
                # Новый формат: (retval, cusps, ascmc, serr)
                retval, cusps, ascmc, serr = result
            else:
                raise ValueError(f"Неверный формат результата от swe.houses: получено {len(result)} элементов, ожидается 2 или 4")
            
            if retval < 0:
                error_msg = serr.decode('utf-8') if isinstance(serr, bytes) else str(serr) if serr else f"Ошибка расчета домов (код: {retval})"
                raise ValueError(f"Ошибка расчета домов: {error_msg}")
            
            # Проверяем, что массивы имеют правильный размер
            if not isinstance(cusps, (list, tuple)):
                raise ValueError(f"Неверный формат массива куспидов: получен {type(cusps).__name__}, ожидается list или tuple")
            
            # Массив куспидов может быть:
            # - 13 элементов: cusps[0] не используется, cusps[1-12] - дома 1-12
            # - 12 элементов: cusps[0-11] - дома 1-12
            if len(cusps) < 12:
                raise ValueError(f"Неверный формат массива куспидов: ожидается минимум 12 элементов, получено {len(cusps)}")
            
            if not isinstance(ascmc, (list, tuple)) or len(ascmc) < 4:
                raise ValueError(f"Неверный формат массива углов: ожидается минимум 4 элемента, получено {len(ascmc) if isinstance(ascmc, (list, tuple)) else 'не массив'}")
            
            houses = {}
            
            # Определяем смещение индексации
            # Если 13 элементов - начинаем с индекса 1, если 12 - с индекса 0
            offset = 1 if len(cusps) == 13 else 0
            
            # Куспиды домов (дома 1-12)
            for house_num in range(1, 13):
                cusp_idx = house_num - 1 + offset  # Для 13 элементов: 0->1, 1->2, ... 11->12
                
                if cusp_idx >= len(cusps):
                    raise ValueError(f"Индекс {cusp_idx} выходит за границы массива куспидов (размер: {len(cusps)})")
                
                cusp_longitude = float(cusps[cusp_idx])
                if cusp_longitude < 0:
                    cusp_longitude += 360
                
                sign_ru, sign_en, degree = self._degrees_to_zodiac_sign(cusp_longitude)
                
                houses[house_num] = {
                    'longitude': round(cusp_longitude, 6),
                    'zodiac_sign': sign_en,
                    'zodiac_sign_ru': sign_ru,
                    'degree_in_sign': round(degree, 2)
                }
            
            # ASC (Ascendant) - куспид 1-го дома
            asc_longitude = float(ascmc[0])
            if asc_longitude < 0:
                asc_longitude += 360
            asc_sign_ru, asc_sign_en, asc_degree = self._degrees_to_zodiac_sign(asc_longitude)
            
            # MC (Midheaven) - куспид 10-го дома
            mc_longitude = float(ascmc[1])
            if mc_longitude < 0:
                mc_longitude += 360
            mc_sign_ru, mc_sign_en, mc_degree = self._degrees_to_zodiac_sign(mc_longitude)
            
            return {
                'houses': houses,
                'ascendant': {
                    'longitude': round(asc_longitude, 6),
                    'zodiac_sign': asc_sign_en,
                    'zodiac_sign_ru': asc_sign_ru,
                    'degree_in_sign': round(asc_degree, 2)
                },
                'midheaven': {
                    'longitude': round(mc_longitude, 6),
                    'zodiac_sign': mc_sign_en,
                    'zodiac_sign_ru': mc_sign_ru,
                    'degree_in_sign': round(mc_degree, 2)
                }
            }
        except Exception as e:
            print(f"⚠️ Ошибка расчета домов: {e}")
            raise ValueError(f"Не удалось рассчитать дома: {e}")

    def _determine_house(
        self, 
        planet_longitude: float, 
        house_cuspids: Dict[int, Dict]
    ) -> int:
        """
        Определяет, в какой дом попадает планета на основе долготы и куспидов домов.
        
        Args:
            planet_longitude: Долгота планеты (0-360)
            house_cuspids: Словарь с куспидами домов {house_number: {'longitude': ...}}
            
        Returns:
            Номер дома (1-12)
        """
        # Создаем список куспидов с их долготами
        cusp_list = []
        for house_num in range(1, 13):
            cusp_longitude = house_cuspids[house_num]['longitude']
            cusp_list.append((house_num, cusp_longitude))
        
        # Сортируем по долготе
        cusp_list.sort(key=lambda x: x[1])
        
        # Находим дом для планеты
        for i in range(len(cusp_list)):
            current_house, current_long = cusp_list[i]
            next_house, next_long = cusp_list[(i + 1) % len(cusp_list)]
            
            # Обработка перехода через 0°
            if next_long < current_long:
                # Переход через 0°
                if planet_longitude >= current_long or planet_longitude < next_long:
                    return current_house
            else:
                # Обычный случай
                if current_long <= planet_longitude < next_long:
                    return current_house
        
        # Fallback: возвращаем дом 1
        return 1

    def _calculate_aspects(
        self, 
        planet_positions: Dict[str, Dict],
        house_cuspids: Optional[Dict[int, Dict]] = None
    ) -> List[Dict]:
        """
        Рассчитывает аспекты между планетами и куспидами домов.
        
        Args:
            planet_positions: Словарь с позициями планет {planet_name: {'longitude': ...}}
            house_cuspids: Опциональный словарь с куспидами домов
            
        Returns:
            Список аспектов
        """
        aspects = []
        
        # Получаем список всех небесных тел (планеты + куспиды)
        celestial_bodies = {}
        celestial_bodies.update(planet_positions)
        
        # Добавляем ASC и MC как "планеты" для аспектов
        if house_cuspids:
            celestial_bodies['ascendant'] = {
                'longitude': house_cuspids[1]['longitude'],  # ASC = куспид 1-го дома
                'zodiac_sign': house_cuspids[1]['zodiac_sign']
            }
            # MC обычно = куспид 10-го дома
            if 10 in house_cuspids:
                celestial_bodies['midheaven'] = {
                    'longitude': house_cuspids[10]['longitude'],
                    'zodiac_sign': house_cuspids[10]['zodiac_sign']
                }
        
        # Создаем список всех пар для проверки
        body_names = list(celestial_bodies.keys())
        
        for i in range(len(body_names)):
            for j in range(i + 1, len(body_names)):
                planet1_name = body_names[i]
                planet2_name = body_names[j]
                
                pos1 = celestial_bodies[planet1_name]['longitude']
                pos2 = celestial_bodies[planet2_name]['longitude']
                
                # Вычисляем угловое расстояние
                diff = abs(pos1 - pos2)
                if diff > 180:
                    diff = 360 - diff
                
                # Проверяем каждый аспект
                for aspect_angle, aspect_name, _ in self._aspects:
                    orb_limit = self._orbs.get(aspect_name, 0)
                    orb = abs(diff - aspect_angle)
                    
                    if orb <= orb_limit:
                        aspects.append({
                            'planet_1_name': planet1_name,
                            'planet_2_name': planet2_name,
                            'aspect_type': aspect_name,
                            'angle': round(aspect_angle, 2),
                            'orb': round(orb, 2)
                        })
                        break  # Найден аспект, переходим к следующей паре
        
        return aspects

    def calculate_natal_chart(
        self,
        birth_date: datetime,
        birth_time_utc: datetime,
        latitude: float,
        longitude: float,
        houses_system: str = 'placidus'
    ) -> Dict:
        """
        Расчет полной натальной карты используя только Swiss Ephemeris.
        
        Args:
            birth_date: Дата рождения
            birth_time_utc: Время рождения в UTC
            latitude: Широта места рождения
            longitude: Долгота места рождения
            houses_system: Система домов (по умолчанию 'placidus')
            
        Returns:
            Dict с полными данными натальной карты
        """
        try:
            # Преобразуем в юлианскую дату для Swiss Ephemeris
            jd = swe.julday(
                birth_time_utc.year,
                birth_time_utc.month,
                birth_time_utc.day,
                birth_time_utc.hour + birth_time_utc.minute / 60.0 + birth_time_utc.second / 3600.0,
                swe.GREG_CAL
            )
            
            # Рассчитываем позиции всех планет через Swiss Ephemeris
            planets_data = {}
            for planet_key in ['sun', 'moon', 'mercury', 'venus', 'mars', 
                              'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'true_node']:
                position = self._calculate_planet_position(planet_key, jd)
                if position:
                    planets_data[planet_key] = position
            
            # Рассчитываем дома
            houses_result = self._calculate_houses(jd, latitude, longitude, houses_system)
            house_cuspids = houses_result['houses']
            
            # Определяем дома для планет
            for planet_key, planet_data in planets_data.items():
                house_num = self._determine_house(
                    planet_data['longitude'],
                    house_cuspids
                )
                planet_data['house'] = house_num
            
            # Рассчитываем аспекты
            aspects = self._calculate_aspects(planets_data, house_cuspids)
            
            return {
                'success': True,
                'planets': planets_data,
                'houses': house_cuspids,
                'angles': {
                    'ascendant': houses_result['ascendant'],
                    'midheaven': houses_result['midheaven']
                },
                'aspects': aspects,
                'metadata': {
                    'calculation_time': datetime.now(pytz.UTC).isoformat(),
                    'coordinates': {'latitude': latitude, 'longitude': longitude},
                    'houses_system': houses_system,
                    'zodiac_type': 'tropical',
                    'ephemeris': 'Swiss Ephemeris'
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _calculate_aspect_between(self, pos1: float, pos2: float, orb: float = 8) -> Optional[Dict]:
        """
        Рассчитывает аспект между двумя позициями (для обратной совместимости)
        """
        diff = abs(pos1 - pos2)
        if diff > 180:
            diff = 360 - diff

        for aspect_angle, aspect_name, aspect_name_ru in self._aspects:
            if abs(diff - aspect_angle) <= orb:
                return {
                    'name': aspect_name,
                    'name_ru': aspect_name_ru,
                    'type': aspect_name,  # Добавляем тип для использования в _calculate_transit_times
                    'angle': aspect_angle,
                    'orb': float(round(abs(diff - aspect_angle), 2))
                }

        return None

    def _calculate_transit_times(
        self,
        planet_key: str,
        natal_longitude: float,
        target_date: datetime,
        aspect_type: str,
        timezone: pytz.BaseTzInfo
    ) -> Optional[Dict]:
        """
        Рассчитывает время начала, окончания и точного аспекта для транзита.
        
        Args:
            planet_key: Ключ транзитной планеты
            natal_longitude: Долгота натальной планеты
            target_date: Дата для поиска транзита
            aspect_type: Тип аспекта (conjunction, opposition, etc.)
            timezone: Временная зона для возврата времени
            
        Returns:
            Словарь с временами транзита или None при ошибке
        """
        try:
            # Находим орбис для данного аспекта
            orb = self.get_orb(aspect_type)
            if orb == 0:
                return None
            
            # Находим точный момент аспекта, итерируя по времени вокруг целевой даты
            # Преобразуем целевую дату в юлианскую дату
            target_jd = swe.julday(
                target_date.year,
                target_date.month,
                target_date.day,
                target_date.hour + target_date.minute / 60.0 + target_date.second / 3600.0,
                swe.GREG_CAL
            )
            
            # Ищем точный момент аспекта, начиная с целевой даты
            exact_jd = None
            min_orb = float('inf')
            
            # Поиск в диапазоне ±3 дня с шагом 1 час
            for day_offset in range(-3, 4):
                for hour_offset in range(0, 24):
                    jd = target_jd + day_offset + hour_offset / 24.0
                    transit_pos = self._calculate_planet_position(planet_key, jd)
                    
                    if transit_pos:
                        transit_lon = transit_pos['longitude']
                        aspect_check = self._calculate_aspect_between(transit_lon, natal_longitude, orb)
                        
                        if aspect_check and aspect_check.get('type') == aspect_type:
                            current_orb = aspect_check.get('orb', float('inf'))
                            if current_orb < min_orb:
                                min_orb = current_orb
                                exact_jd = jd
            
            if exact_jd is None:
                return None
            
            # Рассчитываем временные границы транзита (вход и выход из орбиса)
            # Ищем момент входа в орбис (двигаемся назад от точного аспекта)
            transit_start_jd = None
            for i in range(48):  # Проверяем до 2 дней назад
                jd = exact_jd - i / 24.0
                transit_pos = self._calculate_planet_position(planet_key, jd)
                
                if transit_pos:
                    transit_lon = transit_pos['longitude']
                    aspect_check = self._calculate_aspect_between(transit_lon, natal_longitude, orb)
                    
                    if aspect_check and aspect_check.get('type') == aspect_type:
                        transit_start_jd = jd
                    else:
                        break
            
            # Ищем момент выхода из орбиса (двигаемся вперед от точного аспекта)
            transit_end_jd = None
            for i in range(48):  # Проверяем до 2 дней вперед
                jd = exact_jd + i / 24.0
                transit_pos = self._calculate_planet_position(planet_key, jd)
                
                if transit_pos:
                    transit_lon = transit_pos['longitude']
                    aspect_check = self._calculate_aspect_between(transit_lon, natal_longitude, orb)
                    
                    if aspect_check and aspect_check.get('type') == aspect_type:
                        transit_end_jd = jd
                    else:
                        break
            
            # Преобразуем юлианские даты в datetime с учетом timezone
            result = {}
            
            if exact_jd:
                exact_dt = self._julian_to_datetime(exact_jd, timezone)
                result['exact_time'] = exact_dt.isoformat()
            
            if transit_start_jd:
                start_dt = self._julian_to_datetime(transit_start_jd, timezone)
                result['start_time'] = start_dt.isoformat()
            
            if transit_end_jd:
                end_dt = self._julian_to_datetime(transit_end_jd, timezone)
                result['end_time'] = end_dt.isoformat()
            
            return result if result else None
            
        except Exception as e:
            print(f"⚠️ Ошибка расчета времени транзита: {e}")
            return None

    def _julian_to_datetime(self, jd: float, timezone: pytz.BaseTzInfo) -> datetime:
        """
        Преобразует юлианскую дату в datetime с учетом временной зоны.
        """
        # Используем Swiss Ephemeris для преобразования
        year, month, day, hour_frac = swe.revjul(jd, swe.GREG_CAL)
        hour = int(hour_frac)
        minute = int((hour_frac - hour) * 60)
        second = int(((hour_frac - hour) * 60 - minute) * 60)
        
        dt = datetime(year, month, day, hour, minute, second, tzinfo=pytz.UTC)
        # Конвертируем в нужную временную зону
        return dt.astimezone(timezone)

    def calculate_transits(
        self, 
        natal_chart: Dict, 
        target_date: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone_name: Optional[str] = None
    ) -> Dict:
        """
        Расчет транзитов на конкретную дату используя Swiss Ephemeris.
        
        Args:
            natal_chart: Словарь с данными натальной карты
            target_date: Дата для расчета транзитов (формат: "YYYY-MM-DD")
            latitude: Широта места для расчета (опционально)
            longitude: Долгота места для расчета (опционально)
            timezone_name: Название временной зоны (опционально)
        """
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            # Устанавливаем полдень для транзитов
            target_dt = target_dt.replace(hour=12, minute=0, second=0)
            # Добавляем часовой пояс UTC для транзитов
            target_dt = pytz.UTC.localize(target_dt)
            
            # Определяем временную зону для расчета времени транзитов
            tz = pytz.UTC
            if timezone_name:
                try:
                    tz = pytz.timezone(timezone_name)
                except pytz.exceptions.UnknownTimeZoneError:
                    pass  # Используем UTC по умолчанию
            
            # Преобразуем в юлианскую дату
            jd = swe.julday(
                target_dt.year,
                target_dt.month,
                target_dt.day,
                target_dt.hour + target_dt.minute / 60.0,
                swe.GREG_CAL
            )

            transits_data = {}
            
            # Получаем натальные позиции планет
            natal_planets = natal_chart.get('planets', {})
            
            # Рассчитываем транзитные позиции всех планет
            for planet_key in ['sun', 'moon', 'mercury', 'venus', 'mars', 
                              'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
                if planet_key not in self.sweph_planets:
                    continue
                    
                # Рассчитываем транзитную позицию
                transit_position = self._calculate_planet_position(planet_key, jd)
                
                if transit_position:
                    transit_lon = transit_position['longitude']
                    transit_sign = transit_position['zodiac_sign']
                    is_retrograde = transit_position.get('is_retrograde', False)
                    
                    # Ищем аспект с натальной картой
                    aspect = None
                    transit_start_time = None
                    transit_end_time = None
                    exact_aspect_time = None
                    
                    if planet_key in natal_planets:
                        natal_lon = natal_planets[planet_key].get('longitude', 0)
                        aspect = self._calculate_aspect_between(transit_lon, natal_lon)
                        
                        # Если есть аспект, рассчитываем время начала и окончания транзита
                        if aspect:
                            transit_times = self._calculate_transit_times(
                                planet_key=planet_key,
                                natal_longitude=natal_lon,
                                target_date=target_dt,
                                aspect_type=aspect.get('type'),
                                timezone=tz
                            )
                            if transit_times:
                                transit_start_time = transit_times.get('start_time')
                                transit_end_time = transit_times.get('end_time')
                                exact_aspect_time = transit_times.get('exact_time')
                    
                    transit_info = {
                        'transit_longitude': transit_lon,
                        'transit_sign': transit_sign,
                        'aspect': aspect,
                        'is_retrograde': is_retrograde
                    }
                    
                    # Добавляем время транзита, если оно рассчитано
                    if transit_start_time:
                        transit_info['transit_start_time'] = transit_start_time
                    if transit_end_time:
                        transit_info['transit_end_time'] = transit_end_time
                    if exact_aspect_time:
                        transit_info['exact_aspect_time'] = exact_aspect_time
                    
                    transits_data[planet_key] = transit_info

            return {
                'success': True,
                'date': target_date,
                'transits': transits_data,
                'summary': self._generate_transit_summary(transits_data)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _generate_transit_summary(self, transits: Dict) -> str:
        """Генерация текстового описания транзитов"""
        aspects_found = []

        for planet_key, data in transits.items():
            if data.get('aspect'):
                planet_name = self.planet_names_ru.get(planet_key, 'Планета')
                aspect_name = data['aspect'].get('name_ru', 'аспект')
                aspects_found.append(f"{planet_name} {aspect_name}")

        if aspects_found:
            return f"Ключевые аспекты дня: {', '.join(aspects_found)}"
        else:
            return "Нейтральный день. Хорошее время для рутины и планирования."

    def generate_calendar_with_transits(self, natal_chart: Dict, year: int, month: int) -> Dict:
        """Генерация календаря с транзитами на месяц"""
        days = []

        for day in range(1, 32):
            try:
                date_str = f"{year}-{month:02d}-{day:02d}"
                datetime.strptime(date_str, "%Y-%m-%d")  # Проверка валидности

                # Расчет транзитов на день
                transits = self.calculate_transits(natal_chart, date_str)

                if transits['success']:
                    # Определение цвета дня
                    day_color = self._get_day_color(transits['transits'])

                    days.append({
                        'date': date_str,
                        'color': day_color,
                        'description': transits['summary'],
                        'transits': transits['transits']
                    })

            except ValueError:
                continue

        return {
            'month': f"{year}-{month:02d}",
            'year': year,
            'days': days
        }

    def _get_day_color(self, transits: Dict) -> str:
        """Определение цвета дня на основе транзитов"""
        hard_aspects = ['square', 'opposition']

        hard_count = 0
        for planet_data in transits.values():
            aspect = planet_data.get('aspect')
            if aspect and aspect.get('name') in hard_aspects:
                hard_count += 1

        if hard_count >= 2:
            return 'red'
        elif hard_count == 1:
            return 'blue'
        else:
            return 'green'

    def calculate_contact_chart(self, contact_data: Dict) -> Dict:
        """Расчет натальной карты для контакта (для обратной совместимости)"""
        # Этот метод требует обновления для использования новых параметров
        # Пока оставляем заглушку
        return {'success': False, 'error': 'Метод требует обновления'}


# Глобальный экземпляр сервиса
astro_service = ProfessionalAstroService()
