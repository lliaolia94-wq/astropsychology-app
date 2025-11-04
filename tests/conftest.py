"""
Конфигурация для pytest тестов.
"""
import pytest
from datetime import datetime, date, time
import pytz


# Тестовые данные для известных натальных карт
# Используем стандартные даты для проверки расчетов

TEST_CHARTS = {
    "test_chart_1": {
        "name": "Тестовая карта 1",
        "birth_date": date(1990, 5, 15),
        "birth_time": time(14, 30),
        "birth_time_utc": datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC),  # UTC для Москвы (UTC+3)
        "latitude": 55.7558,  # Москва
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
        # Ожидаемые результаты (примерные, нужно проверить через Swiss Ephemeris)
        "expected_planets": {
            "sun": {
                "zodiac_sign": "taurus",  # Примерно
                "house_range": (1, 12)
            }
        }
    },
    "test_chart_2": {
        "name": "Тестовая карта 2",
        "birth_date": date(1985, 3, 20),
        "birth_time": time(12, 0),
        "birth_time_utc": datetime(1985, 3, 20, 9, 0, 0, tzinfo=pytz.UTC),  # UTC для Москвы
        "latitude": 55.7558,  # Москва
        "longitude": 37.6173,
        "timezone": "Europe/Moscow"
    },
    "test_chart_3": {
        "name": "Тестовая карта 3 (Нью-Йорк)",
        "birth_date": date(1995, 7, 4),
        "birth_time": time(10, 15),
        "birth_time_utc": datetime(1995, 7, 4, 14, 15, 0, tzinfo=pytz.UTC),  # UTC для Нью-Йорка (UTC-4)
        "latitude": 40.7128,  # Нью-Йорк
        "longitude": -74.0060,
        "timezone": "America/New_York"
    }
}


@pytest.fixture
def test_chart_data():
    """Возвращает тестовые данные для карты"""
    return TEST_CHARTS["test_chart_1"]


@pytest.fixture
def all_test_charts():
    """Возвращает все тестовые карты"""
    return TEST_CHARTS

