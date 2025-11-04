"""
Сервис геокодирования для поиска координат и временных зон городов.
Использует локальную базу данных городов (приоритетная реализация).
"""
import json
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class GeocodingService:
    def __init__(self):
        # Путь к файлу с локальной базой городов
        self.cities_db_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'cities_db.json'
        )
        self.cities_db = self._load_cities_db()
        
        # Резервный геокодер (используется только если город не найден в локальной БД)
        self.geocoder = None  # Инициализируем только при необходимости
        
        # Маппинг стран для фильтрации
        self.country_codes = {
            'Россия': 'RU',
            'Russia': 'RU',
            'Украина': 'UA',
            'Ukraine': 'UA',
            'Беларусь': 'BY',
            'Belarus': 'BY',
            'Казахстан': 'KZ',
            'Kazakhstan': 'KZ',
            # Добавить другие страны по необходимости
        }

    def _load_cities_db(self) -> Dict:
        """Загружает локальную базу данных городов из JSON файла"""
        cities_db = {}
        
        try:
            if os.path.exists(self.cities_db_path):
                with open(self.cities_db_path, 'r', encoding='utf-8') as f:
                    cities_db = json.load(f)
                print(f"✅ Загружено {len(cities_db)} городов из JSON файла")
            else:
                print(f"⚠️ Файл базы данных городов не найден: {self.cities_db_path}")
                print(f"   Убедитесь, что файл существует или выполните скрипт загрузки городов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки локальной БД городов: {e}")
        
        return cities_db
    
    def _normalize_city_name(self, city_key: str) -> str:
        """Нормализует название города для сравнения (убирает страну, транслитерацию)"""
        # Убираем страну из ключа
        city_name = city_key.split(',')[0].strip() if ',' in city_key else city_key
        
        # Простая транслитерация для сравнения
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        # Транслитерируем в латиницу для сравнения
        normalized = ''
        for char in city_name.lower():
            normalized += translit_map.get(char, char)
        
        return normalized

    def geocode_location(
        self, 
        location_name: str, 
        country: Optional[str] = None
    ) -> Dict:
        """
        Геокодирует название города/места.
        
        Args:
            location_name: Название города/места
            country: Опциональное название страны для уточнения поиска
            
        Returns:
            Dict с ключами:
            - success: bool
            - data: Dict с lat, lon, timezone, country, location_name (если найдено)
            - error: str (если не найдено)
            - error_code: str (тип ошибки)
            - requires_manual_input: bool (требуется ли ручной ввод)
        """
        if not location_name:
            return {
                'success': False,
                'error': 'Название города не указано',
                'error_code': 'LOCATION_NAME_EMPTY',
                'requires_manual_input': True
            }
        
        location_name = location_name.strip()
        location_lower = location_name.lower()
        # Обрабатываем country: если None или пустая строка, то None
        country_lower = country.lower().strip() if country and country.strip() else None
        
        # Функция для нормализации названия города (убирает ", страна" из ключа)
        def get_city_name_only(key: str) -> str:
            """Извлекает только название города из ключа вида 'Город, Страна'"""
            if ',' in key:
                return key.split(',')[0].strip()
            return key
        
        # Маппинг латиница <-> кириллица для популярных городов
        city_name_variants = {
            'томск': ['tomsk', 'томск'],
            'москва': ['moscow', 'москва'],
            'санкт-петербург': ['saint petersburg', 'санкт-петербург', 'петербург', 'spb'],
            'новосибирск': ['novosibirsk', 'новосибирск'],
            'екатеринбург': ['yekaterinburg', 'екатеринбург'],
            'казань': ['kazan', 'казань'],
            'нижний новгород': ['nizhny novgorod', 'нижний новгород'],
            'рубцовск': ['rubtsovsk', 'рубцовск'],
        }
        
        # Простая транслитерация для создания вариантов поиска
        def transliterate_ru_to_en(text: str) -> str:
            """Простая транслитерация кириллицы в латиницу"""
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            result = ''
            for char in text.lower():
                result += translit_map.get(char, char)
            return result
        
        # Получаем все варианты поискового запроса
        query_variants = [location_lower]
        
        # Добавляем варианты из маппинга, если есть
        if location_lower in city_name_variants:
            query_variants.extend(city_name_variants[location_lower])
        
        # Добавляем транслитерацию (если запрос на кириллице, добавляем латиницу)
        if any(ord(c) > 127 for c in location_lower):  # Есть кириллица
            translit = transliterate_ru_to_en(location_lower)
            if translit != location_lower and translit not in query_variants:
                query_variants.append(translit)
        
        # Ищем точное совпадение в локальной БД
        for city_key, city_data in self.cities_db.items():
            city_name_only = get_city_name_only(city_key)
            city_name_lower = city_name_only.lower()
            city_key_lower = city_key.lower()
            
            # Проверяем точное совпадение с любым вариантом запроса
            matches = False
            for variant in query_variants:
                if variant == city_name_lower or variant == city_key_lower:
                    matches = True
                    break
            
            if matches:
                # Фильтрация по стране, если указана
                if country_lower:
                    city_country = city_data.get('country', '').lower().strip()
                    if city_country != country_lower:
                        continue
                
                # Нашли точное совпадение - возвращаем результат
                result = city_data.copy()
                result['location_name'] = city_name_only  # Используем название без страны
                return {
                    'success': True,
                    'data': result
                }
        
        # Если не найдено точное совпадение, возвращаем ошибку с предложениями
        suggestions = self.search_cities(location_name, country, limit=5)
        return {
            'success': False,
            'error': f'Город "{location_name}" не найден в базе данных',
            'error_code': 'CITY_NOT_FOUND',
            'requires_manual_input': True,
            'suggestions': suggestions
        }

    def search_cities(
        self, 
        query: str, 
        country: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Поиск городов по запросу (для автодополнения в интерфейсе).
        
        Args:
            query: Поисковый запрос
            country: Опциональная фильтрация по стране
            limit: Максимальное количество результатов
            
        Returns:
            Список словарей с информацией о городах
        """
        if not query or len(query.strip()) == 0:
            return []
        
        query_lower = query.strip().lower()
        country_lower = country.lower().strip() if country else None
        results = []
        
        # Проверяем, что база данных не пустая
        if not self.cities_db:
            print("⚠️ База данных городов пуста!")
            return []
        
        # Функция для нормализации названия города (убирает ", страна" из ключа)
        def get_city_name_only(key: str) -> str:
            """Извлекает только название города из ключа вида 'Город, Страна'"""
            if ',' in key:
                return key.split(',')[0].strip()
            return key
        
        # Маппинг латиница <-> кириллица для популярных городов
        city_name_variants = {
            'томск': ['tomsk', 'томск'],
            'москва': ['moscow', 'москва'],
            'санкт-петербург': ['saint petersburg', 'санкт-петербург', 'петербург', 'spb'],
            'новосибирск': ['novosibirsk', 'новосибирск'],
            'екатеринбург': ['yekaterinburg', 'екатеринбург'],
            'казань': ['kazan', 'казань'],
            'нижний новгород': ['nizhny novgorod', 'нижний новгород'],
            'рубцовск': ['rubtsovsk', 'рубцовск'],
        }
        
        # Простая транслитерация для создания вариантов поиска
        def transliterate_ru_to_en(text: str) -> str:
            """Простая транслитерация кириллицы в латиницу"""
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            result = ''
            for char in text.lower():
                result += translit_map.get(char, char)
            return result
        
        # Получаем все варианты поискового запроса
        query_variants = [query_lower]
        
        # Добавляем варианты из маппинга, если есть
        if query_lower in city_name_variants:
            query_variants.extend(city_name_variants[query_lower])
        
        # Добавляем транслитерацию (если запрос на кириллице, добавляем латиницу)
        if any(ord(c) > 127 for c in query_lower):  # Есть кириллица
            translit = transliterate_ru_to_en(query_lower)
            if translit != query_lower and translit not in query_variants:
                query_variants.append(translit)
        
        # Используем нормализованные имена для отслеживания дубликатов
        found_normalized = set()
        
        # Сначала ищем точные совпадения
        for city_key, city_data in self.cities_db.items():
            city_name_only = get_city_name_only(city_key)
            city_name_lower = city_name_only.lower()
            city_key_lower = city_key.lower()
            
            # Нормализуем название для проверки дубликатов
            normalized_name = self._normalize_city_name(city_key)
            
            # Проверяем точное совпадение с любым вариантом запроса
            matches = False
            for variant in query_variants:
                if variant == city_name_lower or variant == city_key_lower:
                    matches = True
                    break
            
            if matches:
                # Фильтрация по стране, если указана
                if country_lower:
                    city_country = city_data.get('country', '').lower().strip()
                    if city_country != country_lower:
                        continue
                
                # Проверяем, не добавили ли мы уже этот город (по нормализованному имени)
                if normalized_name not in found_normalized:
                    result = city_data.copy()
                    result['location_name'] = city_name_only  # Используем название без страны
                    results.insert(0, result)  # Точные совпадения в начале
                    found_normalized.add(normalized_name)
        
        # Затем ищем частичные совпадения (если точное не найдено или нужно больше результатов)
        if len(results) < limit:
            for city_key, city_data in self.cities_db.items():
                city_name_only = get_city_name_only(city_key)
                city_name_lower = city_name_only.lower()
                city_key_lower = city_key.lower()
                normalized_name = self._normalize_city_name(city_key)
                
                # Пропускаем уже найденные города (по нормализованному имени)
                if normalized_name in found_normalized:
                    continue
                
                # Проверяем частичное совпадение в названии или в полном ключе
                # Также проверяем, что запрос содержится в начале названия (для лучшего поиска)
                partial_match = False
                for variant in query_variants:
                    # Проверяем вхождение подстроки
                    if variant in city_name_lower or variant in city_key_lower:
                        partial_match = True
                        break
                    # Проверяем, что название города начинается с запроса (для автодополнения)
                    if city_name_lower.startswith(variant) or city_key_lower.startswith(variant):
                        partial_match = True
                        break
                
                if partial_match:
                    # Фильтрация по стране, если указана
                    if country_lower:
                        city_country = city_data.get('country', '').lower().strip()
                        if city_country != country_lower:
                            continue
                    
                    # Проверяем, что этот город еще не добавлен
                    if normalized_name not in found_normalized:
                        result = city_data.copy()
                        result['location_name'] = city_name_only  # Используем название без страны
                        results.append(result)
                        found_normalized.add(normalized_name)
                        
                        if len(results) >= limit:
                            break
        
        return results[:limit]

    def calculate_utc_time(
        self, 
        birth_date,  # Может быть date или datetime
        birth_time_local,  # Может быть time или datetime
        timezone_name: str
    ) -> datetime:
        """
        Рассчитывает UTC время на основе локального времени и временной зоны.
        
        Args:
            birth_date: Дата рождения (date или datetime)
            birth_time_local: Время рождения (time или datetime)
            timezone_name: Название временной зоны (например, "Europe/Moscow")
            
        Returns:
            datetime объект в UTC
        """
        try:
            from datetime import date, time, datetime
            tz = pytz.timezone(timezone_name)
            
            # Обрабатываем birth_date - может быть date или datetime
            if isinstance(birth_date, datetime):
                date_obj = birth_date.date()
            elif isinstance(birth_date, date):
                date_obj = birth_date
            else:
                raise ValueError(f"Неверный тип birth_date: {type(birth_date)}")
            
            # Обрабатываем birth_time_local - может быть time или datetime
            if isinstance(birth_time_local, datetime):
                time_obj = birth_time_local.time()
            elif isinstance(birth_time_local, time):
                time_obj = birth_time_local
            else:
                raise ValueError(f"Неверный тип birth_time_local: {type(birth_time_local)}")
            
            # Объединяем дату и время
            local_dt = datetime.combine(date_obj, time_obj)
            # Локализуем в указанной временной зоне
            local_dt = tz.localize(local_dt)
            # Конвертируем в UTC
            utc_dt = local_dt.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)  # Убираем timezone для хранения в БД
        except Exception as e:
            print(f"Ошибка расчета UTC времени: {e}")
            # Fallback: возвращаем локальное время как есть
            from datetime import date, time, datetime
            date_obj = birth_date if isinstance(birth_date, date) else birth_date.date()
            time_obj = birth_time_local if isinstance(birth_time_local, time) else birth_time_local.time()
            return datetime.combine(date_obj, time_obj)

    def get_timezone_by_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """
        Определяет временную зону по координатам.
        Использует геокодер как резервный вариант.
        
        Args:
            lat: Широта
            lon: Долгота
            
        Returns:
            Название временной зоны или None
        """
        # Простое определение по долготе (примерное)
        # В реальности лучше использовать библиотеку timezonefinder
        # Но для MVP можно использовать приблизительное определение
        
        # Для России и близлежащих стран
        if 19.0 <= lon <= 169.0:  # Примерные границы
            # Определяем по долготе
            if lon < 30:
                return "Europe/Moscow"
            elif lon < 55:
                return "Europe/Moscow"  # Часть России
            elif lon < 73:
                return "Asia/Yekaterinburg"
            elif lon < 90:
                return "Asia/Novosibirsk"
            elif lon < 110:
                return "Asia/Irkutsk"
            elif lon < 130:
                return "Asia/Yakutsk"
            elif lon < 150:
                return "Asia/Vladivostok"
            else:
                return "Asia/Magadan"
        
        # Для других регионов можно добавить логику
        # Или использовать внешний API
        
        return "UTC"  # Fallback


# Глобальный экземпляр сервиса
geocoding_service = GeocodingService()

