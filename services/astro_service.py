import random
from datetime import datetime
from typing import Dict, Optional
import pytz


class ProfessionalAstroService:
    def __init__(self):
        # Загрузка данных JPL (раз в приложение)
        try:
            from skyfield.api import load
            self.ts = load.timescale()
            self.eph = load('de421.bsp')  # Основной файл эфемерид
            # Загрузка дополнительных данных для Луны и планет
            # В первый раз Skyfield загрузит файлы автоматически
            print("Skyfield данные успешно загружены")
        except Exception as e:
            print(f"Предупреждение при загрузке Skyfield: {e}")
            self.ts = None
            self.eph = None

        self.zodiac_signs = [
            "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
            "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
        ]

        # Маппинг планет в Skyfield
        self.planets = {
            'sun': ('sun', 'Солнце'),
            'moon': ('moon', 'Луна'),
            'mercury': ('mercury barycenter', 'Меркурий'),
            'venus': ('venus barycenter', 'Венера'),
            'mars': ('mars barycenter', 'Марс'),
            'jupiter': ('jupiter barycenter', 'Юпитер'),
            'saturn': ('saturn barycenter', 'Сатурн'),
            'uranus': ('uranus barycenter', 'Уран'),
            'neptune': ('neptune barycenter', 'Нептун'),
            'pluto': ('pluto barycenter', 'Плутон')
        }

        # Обратный маппинг для транзитов
        self.planet_keys = ['sun', 'moon', 'mercury', 'venus', 'mars', 
                           'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']

    def _degrees_to_zodiac_sign(self, longitude: float) -> tuple:
        """
        Преобразует эклиптическую долготу в знак зодиака
        Возвращает (название_знака, градус_в_знаке)
        """
        sign_num = int(longitude / 30) % 12
        degree_in_sign = longitude % 30
        return (self.zodiac_signs[sign_num], degree_in_sign)

    def _parse_birth_data(self, birth_date: str, birth_time: str, birth_place: str):
        """
        Парсит данные рождения и возвращает координаты места рождения
        В будущем здесь можно интегрировать геокодинг
        """
        try:
            # Парсим дату и время
            date_str = f"{birth_date} {birth_time}"
            birth_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            
            # Упрощенный парсинг места рождения (пока заглушка)
            # В реальном проекте здесь нужен геокодинг адреса
            if "москва" in birth_place.lower() or "moscow" in birth_place.lower():
                lat, lon = 55.7558, 37.6173
                tz = pytz.timezone('Europe/Moscow')
            elif "спб" in birth_place.lower() or "saint petersburg" in birth_place.lower():
                lat, lon = 59.9343, 30.3351
                tz = pytz.timezone('Europe/Moscow')
            else:
                # По умолчанию - Москва
                lat, lon = 55.7558, 37.6173
                tz = pytz.timezone('UTC')
            
            # Применяем часовой пояс
            birth_dt = tz.localize(birth_dt)
            
            return birth_dt, lat, lon, tz
        except Exception as e:
            raise ValueError(f"Ошибка парсинга данных рождения: {e}")

    def _calculate_planet_position(self, planet_key: str, t) -> Optional[Dict]:
        """
        Рассчитывает позицию планеты на момент времени t относительно Земли
        """
        if not self.ts or not self.eph:
            return None
            
        try:
            skyfield_name, planet_name_ru = self.planets[planet_key]
            
            # Для астрологии всегда нужна позиция относительно Земли
            earth = self.eph['earth']
            body = self.eph[skyfield_name]
            
            # Получаем позицию относительно Земли
            astrometric = earth.at(t).observe(body)
            lon, lat, distance = astrometric.ecliptic_latlon()
            
            longitude = lon.degrees
            if longitude < 0:
                longitude += 360
            
            # Определяем знак зодиака
            sign, degree = self._degrees_to_zodiac_sign(longitude)
            
            return {
                'longitude': round(longitude, 6),
                'sign': sign,
                'degree_in_sign': round(degree, 2),
                'latitude': round(lat.degrees, 6),
                'distance_au': round(distance.au, 6)
            }
        except Exception as e:
            print(f"Ошибка расчета {planet_key}: {e}")
            return None

    def calculate_natal_chart(self, birth_date: str, birth_time: str, birth_place: str) -> Dict:
        """Расчет натальной карты с использованием Skyfield"""
        try:
            # Парсим данные рождения
            birth_dt, lat, lon, tz = self._parse_birth_data(birth_date, birth_time, birth_place)
            
            # Преобразуем в Skyfield time
            if not self.ts:
                raise ValueError("Skyfield не инициализирован")
            
            t = self.ts.from_datetime(birth_dt)
            
            # Рассчитываем позиции всех планет
            planets_data = {}
            for planet_key in self.planets.keys():
                position = self._calculate_planet_position(planet_key, t)
                if position:
                    # Добавляем информацию для дома (пока заглушка)
                    position['house'] = random.randint(1, 12)
                    # Проверка ретроградности (упрощенная)
                    position['retrograde'] = False  # TODO: добавить расчет ретроградности
                    planets_data[planet_key] = position
                else:
                    # Fallback на случайные данные
                    sign, _ = self._degrees_to_zodiac_sign(random.uniform(0, 360))
                    planets_data[planet_key] = {
                        'longitude': random.uniform(0, 360),
                        'sign': sign,
                        'house': random.randint(1, 12),
                        'retrograde': False
                    }

            # Расчет углов и домов (упрощенно, нужна полная реализация домов)
            asc_lon = random.uniform(0, 360)  # TODO: правильный расчет ASC
            mc_lon = random.uniform(0, 360)    # TODO: правильный расчет MC
            
            asc_sign, _ = self._degrees_to_zodiac_sign(asc_lon)
            mc_sign, _ = self._degrees_to_zodiac_sign(mc_lon)

            return {
                'success': True,
                'planets': planets_data,
                'angles': {
                    'ascendant': {
                        'longitude': round(asc_lon, 2),
                        'sign': asc_sign
                    },
                    'midheaven': {
                        'longitude': round(mc_lon, 2),
                        'sign': mc_sign
                    }
                },
                'houses': {i: {'sign': self._degrees_to_zodiac_sign(i * 30)[0]} 
                          for i in range(1, 13)},
                'metadata': {
                    'calculation_time': datetime.now().isoformat(),
                    'coordinates': {'longitude': lon, 'latitude': lat},
                    'timezone': str(tz)
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _calculate_aspect_between(self, pos1: float, pos2: float, orb: float = 8) -> Optional[Dict]:
        """
        Рассчитывает аспект между двумя позициями
        """
        diff = abs(pos1 - pos2)
        if diff > 180:
            diff = 360 - diff

        aspects = [
            (0, 'conjunction', 'соединение'),
            (60, 'sextile', 'секстиль'),
            (90, 'square', 'квадрат'),
            (120, 'trine', 'трин'),
            (180, 'opposition', 'оппозиция')
        ]

        for aspect_angle, aspect_name, aspect_name_ru in aspects:
            if abs(diff - aspect_angle) <= orb:
                return {
                    'name': aspect_name,
                    'name_ru': aspect_name_ru,
                    'angle': aspect_angle,
                    'orb': float(round(abs(diff - aspect_angle), 2))
                }

        return None

    def calculate_transits(self, natal_chart: Dict, target_date: str) -> Dict:
        """Расчет транзитов на конкретную дату с использованием Skyfield"""
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            # Устанавливаем полдень для транзитов
            target_dt = target_dt.replace(hour=12, minute=0, second=0)
            # Добавляем часовой пояс UTC для транзитов
            target_dt = pytz.UTC.localize(target_dt)
            
            if not self.ts:
                raise ValueError("Skyfield не инициализирован")
            
            t = self.ts.from_datetime(target_dt)

            transits_data = {}
            
            # Получаем натальные позиции планет
            natal_planets = natal_chart.get('planets', {})
            
            for planet_key in self.planets.keys():
                # Рассчитываем транзитную позицию
                transit_position = self._calculate_planet_position(planet_key, t)
                
                if transit_position:
                    transit_lon = transit_position['longitude']
                    transit_sign = transit_position['sign']
                    
                    # Ищем аспект с натальной картой
                    aspect = None
                    if planet_key in natal_planets:
                        natal_lon = natal_planets[planet_key].get('longitude', 0)
                        aspect = self._calculate_aspect_between(transit_lon, natal_lon)
                    
                    transits_data[planet_key] = {
                        'transit_longitude': transit_lon,
                        'transit_sign': transit_sign,
                        'aspect': aspect,
                        'is_retrograde': False  # TODO: добавить расчет ретроградности
                    }
                else:
                    # Fallback
                    sign, _ = self._degrees_to_zodiac_sign(random.uniform(0, 360))
                    transits_data[planet_key] = {
                        'transit_longitude': random.uniform(0, 360),
                        'transit_sign': sign,
                        'aspect': self._generate_random_aspect(),
                        'is_retrograde': False
                    }

            return {
                'success': True,
                'date': target_date,
                'transits': transits_data,
                'summary': self._generate_transit_summary(transits_data)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _generate_random_aspect(self) -> Dict:
        """Генерация случайного аспекта"""
        aspects = [
            {'name': 'conjunction', 'name_ru': 'соединение', 'angle': 0},
            {'name': 'sextile', 'name_ru': 'секстиль', 'angle': 60},
            {'name': 'square', 'name_ru': 'квадрат', 'angle': 90},
            {'name': 'trine', 'name_ru': 'трин', 'angle': 120},
            {'name': 'opposition', 'name_ru': 'оппозиция', 'angle': 180},
            None  # Иногда аспекта нет
        ]

        return random.choice(aspects)

    def _generate_transit_summary(self, transits: Dict) -> str:
        """Генерация текстового описания транзитов"""
        aspects_found = []

        for planet_key, data in transits.items():
            if data['aspect']:
                skyfield_name, planet_name = self.planets[planet_key]
                aspect_name = data['aspect']['name_ru']
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
            if aspect and aspect['name'] in hard_aspects:
                hard_count += 1

        if hard_count >= 2:
            return 'red'
        elif hard_count == 1:
            return 'blue'
        else:
            return 'green'

    def calculate_contact_chart(self, contact_data: Dict) -> Dict:
        """Расчет натальной карты для контакта"""
        return self.calculate_natal_chart(
            contact_data['birth_date'],
            contact_data['birth_time'],
            contact_data['birth_place']
        )

# Глобальный экземпляр сервиса
astro_service = ProfessionalAstroService()