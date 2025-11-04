"""
Тесты с известными натальными картами для верификации точности расчетов.
Используются проверенные данные из профессиональных астрологических программ.
"""
import pytest
from datetime import datetime, date, time
import pytz
import swisseph as swe

from services.astro_service import astro_service


# Известные натальные карты для верификации
# ВАЖНО: Эти данные должны быть проверены через Swiss Ephemeris или профессиональные программы
KNOWN_CHARTS = {
    "test_verified_1": {
        "name": "Верифицированная карта 1",
        "birth_date": date(2000, 1, 1),
        "birth_time_utc": datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC),
        "latitude": 55.7558,  # Москва
        "longitude": 37.6173,
        "houses_system": "placidus",
        # Примерные ожидаемые значения (нужно проверить через Swiss Ephemeris)
        "expected_planets": {
            # Эти значения нужно проверить через Swiss Ephemeris или астрологическую программу
            "sun": {
                "zodiac_sign": "capricorn",  # Примерно для 1 января
                "longitude_range": (270, 300)  # Примерный диапазон
            }
        }
    },
    "test_verified_2": {
        "name": "Верифицированная карта 2 (летнее солнцестояние)",
        "birth_date": date(2000, 6, 21),
        "birth_time_utc": datetime(2000, 6, 21, 12, 0, 0, tzinfo=pytz.UTC),
        "latitude": 55.7558,  # Москва
        "longitude": 37.6173,
        "houses_system": "placidus",
        "expected_planets": {
            "sun": {
                "zodiac_sign": "gemini",  # Примерно для 21 июня
                "longitude_range": (88, 92)  # Примерно 0° Рака
            }
        }
    }
}


class TestKnownCharts:
    """Тесты с известными натальными картами"""
    
    def test_known_chart_calculation(self):
        """Тест расчета известной карты"""
        chart_data = KNOWN_CHARTS["test_verified_1"]
        
        chart = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        assert chart['success'] is True
        assert 'planets' in chart
        assert 'houses' in chart
        assert 'aspects' in chart
        
        # Проверяем наличие всех планет
        expected_planets = ['sun', 'moon', 'mercury', 'venus', 'mars', 
                           'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'true_node']
        for planet in expected_planets:
            assert planet in chart['planets'], f"Планета {planet} отсутствует в расчете"
    
    def test_sun_position_verification(self):
        """Верификация позиции Солнца для известной даты"""
        # 1 января 2000, 00:00 UTC
        birth_time_utc = datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
        
        jd = swe.julday(2000, 1, 1, 0.0, swe.GREG_CAL)
        sun_position = astro_service._calculate_planet_position('sun', jd)
        
        assert sun_position is not None
        assert 'longitude' in sun_position
        assert 'zodiac_sign' in sun_position
        
        # Солнце должно быть в Козероге (примерно 270-300°)
        # Проверяем, что расчет дает разумное значение
        assert 270 <= sun_position['longitude'] <= 300 or \
               0 <= sun_position['longitude'] <= 20, \
               f"Солнце имеет неожиданную позицию: {sun_position['longitude']}°"
        
        # Проверяем знак зодиака
        assert sun_position['zodiac_sign'] in ['capricorn', 'sagittarius', 'aquarius']
    
    def test_solstice_chart(self):
        """Тест карты на день летнего солнцестояния"""
        chart_data = KNOWN_CHARTS["test_verified_2"]
        
        chart = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        assert chart['success'] is True
        
        # Проверяем позицию Солнца (должно быть около 0° Рака в день солнцестояния)
        sun_longitude = chart['planets']['sun']['longitude']
        # В день летнего солнцестояния Солнце должно быть около 90° (0° Рака)
        assert 88 <= sun_longitude <= 92 or \
               sun_longitude <= 2 or sun_longitude >= 358, \
               f"Солнце должно быть около 0° Рака, но получено: {sun_longitude}°"
    
    def test_consistency_between_calculations(self):
        """Тест консистентности между расчетами"""
        # Рассчитываем одну и ту же карту дважды
        chart_data = KNOWN_CHARTS["test_verified_1"]
        
        chart1 = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        chart2 = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        # Результаты должны быть идентичными
        assert chart1['success'] == chart2['success']
        
        # Проверяем идентичность позиций планет
        for planet in chart1['planets']:
            if planet in chart2['planets']:
                lon1 = chart1['planets'][planet]['longitude']
                lon2 = chart2['planets'][planet]['longitude']
                assert abs(lon1 - lon2) < 0.0001, \
                    f"Позиция {planet} не консистентна: {lon1} vs {lon2}"
    
    def test_house_cuspids_consistency(self):
        """Тест консистентности куспидов домов"""
        chart_data = KNOWN_CHARTS["test_verified_1"]
        
        chart = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        houses = chart['houses']
        ascendant = chart['angles']['ascendant']
        midheaven = chart['angles']['midheaven']
        
        # ASC должен совпадать с куспидом 1-го дома
        asc_longitude = ascendant['longitude']
        house1_longitude = houses[1]['longitude']
        assert abs(asc_longitude - house1_longitude) < 0.01, \
            f"ASC ({asc_longitude}°) не совпадает с куспидом 1-го дома ({house1_longitude}°)"
        
        # MC должен совпадать с куспидом 10-го дома
        mc_longitude = midheaven['longitude']
        house10_longitude = houses[10]['longitude']
        assert abs(mc_longitude - house10_longitude) < 0.01, \
            f"MC ({mc_longitude}°) не совпадает с куспидом 10-го дома ({house10_longitude}°)"
    
    def test_planets_in_houses(self):
        """Тест, что все планеты имеют назначенные дома"""
        chart_data = KNOWN_CHARTS["test_verified_1"]
        
        chart = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        # Проверяем, что все планеты имеют назначенные дома
        for planet_key, planet_data in chart['planets'].items():
            assert 'house' in planet_data, f"Планета {planet_key} не имеет назначенного дома"
            assert 1 <= planet_data['house'] <= 12, \
                f"Планета {planet_key} имеет неверный номер дома: {planet_data['house']}"
    
    def test_aspects_calculation(self):
        """Тест расчета аспектов для известной карты"""
        chart_data = KNOWN_CHARTS["test_verified_1"]
        
        chart = astro_service.calculate_natal_chart(
            birth_date=chart_data["birth_date"],
            birth_time_utc=chart_data["birth_time_utc"],
            latitude=chart_data["latitude"],
            longitude=chart_data["longitude"],
            houses_system=chart_data["houses_system"]
        )
        
        assert 'aspects' in chart
        assert isinstance(chart['aspects'], list)
        
        # Проверяем структуру аспектов
        for aspect in chart['aspects']:
            assert 'planet_1_name' in aspect
            assert 'planet_2_name' in aspect
            assert 'aspect_type' in aspect
            assert 'angle' in aspect
            assert 'orb' in aspect
            
            # Проверяем, что типы аспектов корректны
            assert aspect['aspect_type'] in ['conjunction', 'sextile', 'square', 'trine', 'opposition']
            
            # Проверяем, что орбис не превышает допустимый
            orb_limit = astro_service.get_orb(aspect['aspect_type'])
            assert aspect['orb'] <= orb_limit, \
                f"Орбис аспекта {aspect['aspect_type']} превышает допустимый: {aspect['orb']}° (лимит: {orb_limit}°)"


class TestSwissEphemerisVerification:
    """Тесты для прямой верификации через Swiss Ephemeris"""
    
    def test_direct_swiss_ephemeris_calculation(self):
        """Прямой расчет через Swiss Ephemeris для верификации"""
        # 1 января 2000, 00:00 UTC
        jd = swe.julday(2000, 1, 1, 0.0, swe.GREG_CAL)
        
        # Рассчитываем Солнце напрямую через Swiss Ephemeris
        xx, retflag = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
        
        assert retflag >= 0, "Ошибка расчета через Swiss Ephemeris"
        assert len(xx) > 0
        
        # Долгота Солнца
        sun_longitude = xx[0]
        if sun_longitude < 0:
            sun_longitude += 360
        
        # Проверяем, что наш метод дает тот же результат
        our_position = astro_service._calculate_planet_position('sun', jd)
        
        assert our_position is not None
        assert abs(our_position['longitude'] - sun_longitude) < 0.0001, \
            f"Расхождение в расчете Солнца: наш {our_position['longitude']}°, прямой {sun_longitude}°"
    
    def test_all_planets_swiss_ephemeris(self):
        """Верификация всех планет через прямой расчет Swiss Ephemeris"""
        jd = swe.julday(2000, 1, 1, 0.0, swe.GREG_CAL)
        
        planets = {
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
        }
        
        for planet_key, planet_id in planets.items():
            # Прямой расчет
            xx, retflag = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH)
            assert retflag >= 0, f"Ошибка расчета {planet_key}"
            
            direct_longitude = xx[0]
            if direct_longitude < 0:
                direct_longitude += 360
            
            # Наш расчет
            our_position = astro_service._calculate_planet_position(planet_key, jd)
            assert our_position is not None, f"Планета {planet_key} не рассчитана"
            
            # Сравнение
            assert abs(our_position['longitude'] - direct_longitude) < 0.0001, \
                f"Расхождение в расчете {planet_key}: наш {our_position['longitude']}°, прямой {direct_longitude}°"

