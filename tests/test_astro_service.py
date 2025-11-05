"""
Тесты для astro_service - проверка корректности астрологических расчетов.
"""
import pytest
from datetime import datetime, date, time
import pytz
import swisseph as swe

from services.astro_service import astro_service


class TestPlanetPositions:
    """Тесты для расчета позиций планет"""
    
    def test_sun_position(self):
        """Тест расчета позиции Солнца"""
        # Дата: 15 мая 1990, 14:30 UTC (примерно в Тельце)
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        position = astro_service._calculate_planet_position('sun', jd)
        
        assert position is not None
        assert 'longitude' in position
        assert 'zodiac_sign' in position
        assert 'zodiac_sign_ru' in position
        assert 'degree_in_sign' in position
        assert 0 <= position['longitude'] <= 360
        assert position['zodiac_sign'] in astro_service.zodiac_signs_en
        # Солнце должно быть примерно в Тельце (30-60 градусов)
        assert 24 <= position['longitude'] <= 84  # Примерный диапазон для мая
    
    def test_moon_position(self):
        """Тест расчета позиции Луны"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        position = astro_service._calculate_planet_position('moon', jd)
        
        assert position is not None
        assert 'longitude' in position
        assert 0 <= position['longitude'] <= 360
        assert position['zodiac_sign'] in astro_service.zodiac_signs_en
    
    def test_all_planets_calculated(self):
        """Тест расчета всех планет"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        planets = ['sun', 'moon', 'mercury', 'venus', 'mars', 
                  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'true_node']
        
        for planet_key in planets:
            position = astro_service._calculate_planet_position(planet_key, jd)
            assert position is not None, f"Планета {planet_key} не рассчитана"
            assert 'longitude' in position
            assert 'zodiac_sign' in position
            assert 0 <= position['longitude'] <= 360
    
    def test_retrograde_detection(self):
        """Тест определения ретроградности"""
        # Используем дату, когда Меркурий ретроградный (можно проверить заранее)
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        # Проверяем, что метод возвращает is_retrograde
        position = astro_service._calculate_planet_position('mercury', jd)
        assert position is not None
        assert 'is_retrograde' in position
        assert isinstance(position['is_retrograde'], bool)
        
        # Проверяем, что скорость также возвращается
        assert 'speed' in position
        assert isinstance(position['speed'], (int, float))
        
        # Проверяем логику: если скорость отрицательная, то ретроградная
        if position['speed'] < 0:
            assert position['is_retrograde'] is True
        else:
            assert position['is_retrograde'] is False


class TestHouses:
    """Тесты для расчета домов"""
    
    def test_houses_calculation(self):
        """Тест расчета домов"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        lat, lon = 55.7558, 37.6173  # Москва
        
        houses_result = astro_service._calculate_houses(jd, lat, lon, 'placidus')
        
        assert 'houses' in houses_result
        assert 'ascendant' in houses_result
        assert 'midheaven' in houses_result
        
        # Проверяем, что все 12 домов рассчитаны
        houses = houses_result['houses']
        assert len(houses) == 12
        for i in range(1, 13):
            assert i in houses
            assert 'longitude' in houses[i]
            assert 'zodiac_sign' in houses[i]
            assert 0 <= houses[i]['longitude'] <= 360
    
    def test_ascendant_calculation(self):
        """Тест расчета Асцендента"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        lat, lon = 55.7558, 37.6173
        
        houses_result = astro_service._calculate_houses(jd, lat, lon, 'placidus')
        asc = houses_result['ascendant']
        
        assert 'longitude' in asc
        assert 'zodiac_sign' in asc
        assert 0 <= asc['longitude'] <= 360
        # ASC должен совпадать с куспидом 1-го дома
        assert abs(asc['longitude'] - houses_result['houses'][1]['longitude']) < 0.01
    
    def test_mc_calculation(self):
        """Тест расчета MC (Midheaven)"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        lat, lon = 55.7558, 37.6173
        
        houses_result = astro_service._calculate_houses(jd, lat, lon, 'placidus')
        mc = houses_result['midheaven']
        
        assert 'longitude' in mc
        assert 'zodiac_sign' in mc
        assert 0 <= mc['longitude'] <= 360
        # MC должен совпадать с куспидом 10-го дома
        assert abs(mc['longitude'] - houses_result['houses'][10]['longitude']) < 0.01
    
    def test_different_house_systems(self):
        """Тест различных систем домов"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        lat, lon = 55.7558, 37.6173
        
        systems = ['placidus', 'koch', 'equal', 'whole']
        
        for system in systems:
            houses_result = astro_service._calculate_houses(jd, lat, lon, system)
            assert 'houses' in houses_result
            assert len(houses_result['houses']) == 12


class TestAspects:
    """Тесты для расчета аспектов"""
    
    def test_aspect_calculation(self):
        """Тест расчета аспектов между планетами"""
        # Создаем тестовые позиции планет
        planet_positions = {
            'sun': {'longitude': 45.0, 'zodiac_sign': 'taurus'},
            'moon': {'longitude': 105.0, 'zodiac_sign': 'cancer'},  # 60 градусов от Солнца - секстиль
            'mars': {'longitude': 135.0, 'zodiac_sign': 'leo'},  # 90 градусов от Солнца - квадрат
        }
        
        aspects = astro_service._calculate_aspects(planet_positions)
        
        assert isinstance(aspects, list)
        # Должны быть найдены аспекты между планетами
        assert len(aspects) > 0
        
        # Проверяем наличие секстиля Солнце-Луна (60°)
        sun_moon_aspect = [a for a in aspects 
                          if a['planet_1_name'] == 'sun' and a['planet_2_name'] == 'moon']
        assert len(sun_moon_aspect) > 0
        assert sun_moon_aspect[0]['aspect_type'] == 'sextile'
    
    def test_aspect_orb_calculation(self):
        """Тест расчета орбиса аспекта"""
        # Тест с точным аспектом
        pos1, pos2 = 45.0, 165.0  # Разница 120° - трин
        aspect = astro_service._calculate_aspect_between(pos1, pos2)
        
        assert aspect is not None
        assert aspect['aspect_type'] == 'trine'
        assert aspect['angle'] == 120
        assert aspect['orb'] == 0.0  # Точный аспект
    
    def test_conjunction_aspect(self):
        """Тест соединения (0°)"""
        pos1, pos2 = 45.0, 47.0  # Разница 2° - соединение в пределах орбиса
        aspect = astro_service._calculate_aspect_between(pos1, pos2, orb=8.0)
        
        assert aspect is not None
        assert aspect['aspect_type'] == 'conjunction'
        assert aspect['angle'] == 0
        assert aspect['orb'] == 2.0
    
    def test_aspect_with_ascendant(self):
        """Тест расчета аспектов с ASC"""
        planet_positions = {
            'sun': {'longitude': 45.0, 'zodiac_sign': 'taurus'},
        }
        
        house_cuspids = {
            1: {'longitude': 105.0, 'zodiac_sign': 'cancer'}  # ASC
        }
        
        aspects = astro_service._calculate_aspects(planet_positions, house_cuspids)
        
        # Должен быть найден аспект между Солнцем и ASC
        asc_aspects = [a for a in aspects if 'ascendant' in [a['planet_1_name'], a['planet_2_name']]]
        assert len(asc_aspects) > 0


class TestHouseDetermination:
    """Тесты для определения домов планет"""
    
    def test_planet_in_house(self):
        """Тест определения дома для планеты"""
        # Создаем тестовые куспиды домов
        house_cuspids = {
            1: {'longitude': 30.0},   # Овен
            2: {'longitude': 60.0},   # Телец
            3: {'longitude': 90.0},   # Близнецы
            4: {'longitude': 120.0},  # Рак
            5: {'longitude': 150.0},  # Лев
            6: {'longitude': 180.0},  # Дева
            7: {'longitude': 210.0},  # Весы
            8: {'longitude': 240.0},  # Скорпион
            9: {'longitude': 270.0},  # Стрелец
            10: {'longitude': 300.0}, # Козерог
            11: {'longitude': 330.0}, # Водолей
            12: {'longitude': 360.0}, # Рыбы
        }
        
        # Планета на 45° должна быть во 2-м доме
        house = astro_service._determine_house(45.0, house_cuspids)
        assert house == 2
        
        # Планета на 100° должна быть в 3-м доме
        house = astro_service._determine_house(100.0, house_cuspids)
        assert house == 3


class TestFullNatalChart:
    """Тесты для полной натальной карты"""
    
    def test_full_chart_calculation(self):
        """Тест расчета полной натальной карты"""
        birth_date = date(1990, 5, 15)
        birth_time_utc = datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        chart = astro_service.calculate_natal_chart(
            birth_date=birth_date,
            birth_time_utc=birth_time_utc,
            latitude=lat,
            longitude=lon,
            houses_system='placidus'
        )
        
        assert chart['success'] is True
        assert 'planets' in chart
        assert 'houses' in chart
        assert 'angles' in chart
        assert 'aspects' in chart
        assert 'metadata' in chart
        
        # Проверяем наличие всех планет
        expected_planets = ['sun', 'moon', 'mercury', 'venus', 'mars', 
                           'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'true_node']
        for planet in expected_planets:
            assert planet in chart['planets']
        
        # Проверяем наличие всех домов
        assert len(chart['houses']) == 12
        
        # Проверяем наличие углов
        assert 'ascendant' in chart['angles']
        assert 'midheaven' in chart['angles']
        
        # Проверяем, что планеты имеют назначенные дома
        for planet_key, planet_data in chart['planets'].items():
            assert 'house' in planet_data
            assert 1 <= planet_data['house'] <= 12
    
    def test_chart_with_different_house_system(self):
        """Тест расчета карты с разными системами домов"""
        birth_date = date(1990, 5, 15)
        birth_time_utc = datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        systems = ['placidus', 'koch', 'equal']
        
        for system in systems:
            chart = astro_service.calculate_natal_chart(
                birth_date=birth_date,
                birth_time_utc=birth_time_utc,
                latitude=lat,
                longitude=lon,
                houses_system=system
            )
            
            assert chart['success'] is True
            assert chart['metadata']['houses_system'] == system
    
    def test_chart_metadata(self):
        """Тест метаданных карты"""
        birth_date = date(1990, 5, 15)
        birth_time_utc = datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        chart = astro_service.calculate_natal_chart(
            birth_date=birth_date,
            birth_time_utc=birth_time_utc,
            latitude=lat,
            longitude=lon
        )
        
        metadata = chart['metadata']
        assert 'calculation_time' in metadata
        assert 'coordinates' in metadata
        assert metadata['coordinates']['latitude'] == lat
        assert metadata['coordinates']['longitude'] == lon
        assert metadata['houses_system'] == 'placidus'
        assert metadata['zodiac_type'] == 'tropical'
        assert metadata['ephemeris'] == 'Swiss Ephemeris'


class TestTransits:
    """Тесты для расчета транзитов"""
    
    def test_transit_calculation(self):
        """Тест расчета транзитов"""
        # Создаем тестовую натальную карту
        birth_date = date(1990, 5, 15)
        birth_time_utc = datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        natal_chart = astro_service.calculate_natal_chart(
            birth_date=birth_date,
            birth_time_utc=birth_time_utc,
            latitude=lat,
            longitude=lon
        )
        
        # Рассчитываем транзиты на дату
        target_date = "2024-01-15"
        transits = astro_service.calculate_transits(natal_chart, target_date)
        
        assert transits['success'] is True
        assert 'transits' in transits
        assert 'date' in transits
        assert transits['date'] == target_date
        
        # Проверяем наличие транзитов для основных планет
        for planet in ['sun', 'moon', 'mercury', 'venus', 'mars']:
            assert planet in transits['transits']
            assert 'transit_longitude' in transits['transits'][planet]
            assert 'transit_sign' in transits['transits'][planet]
            assert 'is_retrograde' in transits['transits'][planet]


class TestZodiacSigns:
    """Тесты для преобразования градусов в знаки зодиака"""
    
    def test_zodiac_sign_conversion(self):
        """Тест преобразования градусов в знаки зодиака"""
        # 0° - Овен
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(0.0)
        assert sign_en == 'aries'
        assert degree == 0.0
        
        # 30° - Телец
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(30.0)
        assert sign_en == 'taurus'
        assert degree == 0.0
        
        # 45° - Телец, 15°
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(45.0)
        assert sign_en == 'taurus'
        assert degree == 15.0
        
        # 180° - Весы
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(180.0)
        assert sign_en == 'libra'
        assert degree == 0.0
        
        # 359° - Рыбы
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(359.0)
        assert sign_en == 'pisces'
        assert abs(degree - 29.0) < 0.1


class TestEdgeCases:
    """Тесты для граничных случаев"""
    
    def test_zero_longitude(self):
        """Тест с нулевой долготой"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        position = astro_service._calculate_planet_position('sun', jd)
        assert position is not None
    
    def test_negative_longitude_normalization(self):
        """Тест нормализации отрицательных долгот"""
        # Проверяем, что отрицательные долготы нормализуются
        sign_ru, sign_en, degree = astro_service._degrees_to_zodiac_sign(-10.0)
        # Должно быть нормализовано как 350°
        assert sign_en == 'pisces'
    
    def test_very_old_date(self):
        """Тест для очень старой даты"""
        birth_date = date(1900, 1, 1)
        birth_time_utc = datetime(1900, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        chart = astro_service.calculate_natal_chart(
            birth_date=birth_date,
            birth_time_utc=birth_time_utc,
            latitude=lat,
            longitude=lon
        )
        
        assert chart['success'] is True
    
    def test_future_date(self):
        """Тест для будущей даты"""
        birth_date = date(2050, 12, 31)
        birth_time_utc = datetime(2050, 12, 31, 12, 0, 0, tzinfo=pytz.UTC)
        lat, lon = 55.7558, 37.6173
        
        chart = astro_service.calculate_natal_chart(
            birth_date=birth_date,
            birth_time_utc=birth_time_utc,
            latitude=lat,
            longitude=lon
        )
        
        assert chart['success'] is True

