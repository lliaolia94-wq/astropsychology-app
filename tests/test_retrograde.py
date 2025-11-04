"""
Тесты для определения ретроградности планет.
"""
import pytest
from datetime import datetime, date
import pytz
import swisseph as swe

from services.astro_service import astro_service


class TestRetrogradeDetection:
    """Тесты для определения ретроградности"""
    
    def test_retrograde_flag_in_calculation(self):
        """Тест, что флаг FLG_SPEED используется в расчете"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        # Проверяем, что все планеты имеют поле is_retrograde
        planets = ['mercury', 'venus', 'mars', 'jupiter', 'saturn']
        
        for planet_key in planets:
            position = astro_service._calculate_planet_position(planet_key, jd)
            assert position is not None, f"Планета {planet_key} не рассчитана"
            assert 'is_retrograde' in position, f"Планета {planet_key} не имеет поля is_retrograde"
            assert isinstance(position['is_retrograde'], bool), \
                f"is_retrograde должен быть bool, получен {type(position['is_retrograde])}"
    
    def test_retrograde_vs_direct_calculation(self):
        """Сравнение определения ретроградности через наш метод и напрямую"""
        # Используем дату, когда Меркурий может быть ретроградным
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        # Прямой расчет через Swiss Ephemeris
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        xx, retflag = swe.calc_ut(jd, swe.MERCURY, flags)
        
        assert retflag >= 0, "Ошибка расчета Меркурия"
        
        # Определяем ретроградность напрямую
        direct_retrograde = xx[3] < 0 if len(xx) > 3 else False
        
        # Наш расчет
        our_position = astro_service._calculate_planet_position('mercury', jd)
        
        assert our_position is not None
        assert our_position['is_retrograde'] == direct_retrograde, \
            f"Расхождение в определении ретроградности: наш {our_position['is_retrograde']}, прямой {direct_retrograde}"
    
    def test_sun_and_moon_never_retrograde(self):
        """Тест, что Солнце и Луна никогда не ретроградные"""
        # Проверяем несколько дат
        test_dates = [
            (1990, 5, 15, 14.5),
            (2000, 1, 1, 12.0),
            (2020, 6, 21, 12.0),
        ]
        
        for year, month, day, hour in test_dates:
            jd = swe.julday(year, month, day, hour, swe.GREG_CAL)
            
            sun_position = astro_service._calculate_planet_position('sun', jd)
            moon_position = astro_service._calculate_planet_position('moon', jd)
            
            assert sun_position is not None
            assert moon_position is not None
            
            assert sun_position['is_retrograde'] is False, \
                f"Солнце не должно быть ретроградным ({year}-{month}-{day})"
            assert moon_position['is_retrograde'] is False, \
                f"Луна не должна быть ретроградной ({year}-{month}-{day})"
    
    def test_retrograde_in_natal_chart(self):
        """Тест, что ретроградность сохраняется в натальной карте"""
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
        
        # Проверяем, что все планеты имеют поле is_retrograde
        for planet_key, planet_data in chart['planets'].items():
            assert 'is_retrograde' in planet_data, \
                f"Планета {planet_key} не имеет поля is_retrograde в натальной карте"
            assert isinstance(planet_data['is_retrograde'], bool)
    
    def test_retrograde_speed_value(self):
        """Тест, что скорость планеты правильно извлекается"""
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        # Прямой расчет
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        xx, retflag = swe.calc_ut(jd, swe.MERCURY, flags)
        
        assert retflag >= 0
        direct_speed = xx[3] if len(xx) > 3 else 0.0
        
        # Наш расчет
        position = astro_service._calculate_planet_position('mercury', jd)
        
        assert position is not None
        assert 'speed' in position
        
        # Скорость должна совпадать (с небольшой погрешностью из-за округления)
        assert abs(position['speed'] - direct_speed) < 0.001, \
            f"Расхождение в скорости: наш {position['speed']}, прямой {direct_speed}"
    
    def test_retrograde_for_outer_planets(self):
        """Тест ретроградности для внешних планет (Юпитер, Сатурн, Уран, Нептун, Плутон)"""
        # Внешние планеты часто ретроградные
        jd = swe.julday(1990, 5, 15, 14.5, swe.GREG_CAL)
        
        outer_planets = ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto']
        
        for planet_key in outer_planets:
            position = astro_service._calculate_planet_position(planet_key, jd)
            
            assert position is not None
            assert 'is_retrograde' in position
            assert isinstance(position['is_retrograde'], bool)
            
            # Проверяем через прямой расчет
            planet_id = astro_service.sweph_planets[planet_key]
            flags = swe.FLG_SWIEPH | swe.FLG_SPEED
            xx, retflag = swe.calc_ut(jd, planet_id, flags)
            
            assert retflag >= 0
            expected_retrograde = xx[3] < 0 if len(xx) > 3 else False
            
            assert position['is_retrograde'] == expected_retrograde, \
                f"Расхождение для {planet_key}: наш {position['is_retrograde']}, ожидалось {expected_retrograde}"

