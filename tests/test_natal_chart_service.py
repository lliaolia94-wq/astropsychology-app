"""
Тесты для natal_chart_service - проверка бизнес-логики расчета и сохранения карт.
"""
import pytest
from datetime import datetime, date, time
import pytz
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from services.natal_chart_service import natal_chart_service
from database.models import User, NatalChart


class TestNatalChartService:
    """Тесты для сервиса натальных карт"""
    
    @pytest.fixture
    def mock_user(self):
        """Создает мок-объект пользователя"""
        user = Mock(spec=User)
        user.id = 1
        user.birth_date_detailed = date(1990, 5, 15)
        user.birth_time_detailed = time(14, 30)
        user.birth_time_utc = datetime(1990, 5, 15, 11, 30, 0, tzinfo=pytz.UTC)
        user.birth_latitude = 55.7558
        user.birth_longitude = 37.6173
        user.birth_location_name = "Москва"
        user.birth_country = "Россия"
        user.timezone_name = "Europe/Moscow"
        return user
    
    @pytest.fixture
    def mock_db(self):
        """Создает мок-объект сессии БД"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    def test_calculate_chart_missing_data(self, mock_user, mock_db):
        """Тест расчета карты при отсутствии данных"""
        mock_user.birth_date_detailed = None
        
        result = natal_chart_service.calculate_and_save_chart(
            user=mock_user,
            db=mock_db,
            force_recalculate=False
        )
        
        assert result['success'] is False
        assert 'Не указаны дата и время рождения' in result['error']
    
    def test_calculate_chart_missing_coordinates(self, mock_user, mock_db):
        """Тест расчета карты при отсутствии координат"""
        mock_user.birth_latitude = None
        mock_user.birth_longitude = None
        
        result = natal_chart_service.calculate_and_save_chart(
            user=mock_user,
            db=mock_db,
            force_recalculate=False
        )
        
        assert result['success'] is False
        assert 'Не указаны координаты места рождения' in result['error']
    
    def test_calculate_chart_success(self, mock_user, mock_db):
        """Тест успешного расчета карты"""
        # Мокаем расчет карты
        with patch.object(natal_chart_service.astro_service, 'calculate_natal_chart') as mock_calc:
            mock_calc.return_value = {
                'success': True,
                'planets': {
                    'sun': {'longitude': 45.0, 'zodiac_sign': 'taurus', 'house': 2}
                },
                'houses': {
                    1: {'longitude': 30.0, 'zodiac_sign': 'aries'},
                    2: {'longitude': 60.0, 'zodiac_sign': 'taurus'}
                },
                'angles': {
                    'ascendant': {'longitude': 30.0, 'zodiac_sign': 'aries'},
                    'midheaven': {'longitude': 120.0, 'zodiac_sign': 'cancer'}
                },
                'aspects': [],
                'metadata': {'zodiac_type': 'tropical'}
            }
            
            result = natal_chart_service.calculate_and_save_chart(
                user=mock_user,
                db=mock_db,
                force_recalculate=False
            )
            
            # Проверяем, что метод расчета был вызван
            mock_calc.assert_called_once()
            assert result['success'] is True
            assert 'chart_id' in result or result.get('message') == 'Карта уже существует'
    
    def test_get_chart_for_user_not_found(self, mock_user, mock_db):
        """Тест получения карты, когда она не найдена"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = natal_chart_service.get_chart_for_user(mock_user, mock_db)
        
        assert result is None
    
    def test_get_chart_for_user_success(self, mock_user, mock_db):
        """Тест успешного получения карты"""
        # Создаем мок-объект карты
        mock_chart = Mock(spec=NatalChart)
        mock_chart.id = 1
        mock_chart.calculated_at = datetime.now()
        mock_chart.houses_system = 'placidus'
        mock_chart.zodiac_type = 'tropical'
        
        # Мокаем связанные объекты
        mock_planet_pos = Mock()
        mock_planet_pos.planet_name = 'sun'
        mock_planet_pos.longitude = 45.0
        mock_planet_pos.zodiac_sign = 'taurus'
        mock_planet_pos.house = 2
        
        mock_chart.planet_positions = [mock_planet_pos]
        mock_chart.aspects = []
        mock_chart.house_cuspids = []
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chart
        
        result = natal_chart_service.get_chart_for_user(mock_user, mock_db)
        
        assert result is not None
        assert result['chart_id'] == 1
        assert 'planets' in result
        assert 'sun' in result['planets']

