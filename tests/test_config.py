"""
Тесты для конфигурации орбисов аспектов.
"""
import pytest
import os
from unittest.mock import patch

from config import AstrologyConfig, config
from services.astro_service import astro_service


class TestAstrologyConfig:
    """Тесты для конфигурации"""
    
    def test_default_orbs(self):
        """Тест значений орбисов по умолчанию"""
        orbs = config.get_orbs()
        
        assert 'conjunction' in orbs
        assert 'opposition' in orbs
        assert 'trine' in orbs
        assert 'square' in orbs
        assert 'sextile' in orbs
        
        # Проверяем значения по умолчанию
        assert orbs['conjunction'] == 8.0
        assert orbs['opposition'] == 8.0
        assert orbs['trine'] == 8.0
        assert orbs['square'] == 8.0
        assert orbs['sextile'] == 6.0
    
    def test_get_orb(self):
        """Тест получения орбиса для конкретного аспекта"""
        orb = config.get_orb('conjunction')
        assert orb == 8.0
        
        orb = config.get_orb('sextile')
        assert orb == 6.0
        
        # Несуществующий аспект
        orb = config.get_orb('nonexistent')
        assert orb == 0.0
    
    @patch.dict(os.environ, {'ASPECT_ORB_CONJUNCTION': '10.0'})
    def test_env_override(self):
        """Тест переопределения орбиса через переменную окружения"""
        # Перезагружаем конфигурацию
        test_config = AstrologyConfig()
        orbs = test_config.get_orbs()
        
        assert orbs['conjunction'] == 10.0
        assert orbs['opposition'] == 8.0  # Остальные без изменений
    
    @patch.dict(os.environ, {
        'ASPECT_ORB_CONJUNCTION': '10.0',
        'ASPECT_ORB_SEXTILE': '5.0'
    })
    def test_multiple_env_overrides(self):
        """Тест переопределения нескольких орбисов"""
        test_config = AstrologyConfig()
        orbs = test_config.get_orbs()
        
        assert orbs['conjunction'] == 10.0
        assert orbs['sextile'] == 5.0
        assert orbs['square'] == 8.0  # Без изменений
    
    @patch.dict(os.environ, {'ASPECT_ORB_CONJUNCTION': 'invalid'})
    def test_invalid_env_value(self):
        """Тест обработки неверного значения в переменной окружения"""
        test_config = AstrologyConfig()
        orbs = test_config.get_orbs()
        
        # Должно использовать значение по умолчанию
        assert orbs['conjunction'] == 8.0


class TestAstroServiceConfig:
    """Тесты для использования конфигурации в astro_service"""
    
    def test_service_uses_config(self):
        """Тест, что сервис использует конфигурацию"""
        orbs = astro_service.ORBS
        assert isinstance(orbs, dict)
        assert 'conjunction' in orbs
    
    def test_get_orb_method(self):
        """Тест метода get_orb"""
        orb = astro_service.get_orb('conjunction')
        assert orb == 8.0
        
        orb = astro_service.get_orb('sextile')
        assert orb == 6.0
    
    def test_set_orb_method(self):
        """Тест динамического изменения орбиса"""
        original_orb = astro_service.get_orb('conjunction')
        
        # Изменяем орбис
        astro_service.set_orb('conjunction', 10.0)
        assert astro_service.get_orb('conjunction') == 10.0
        
        # Восстанавливаем
        astro_service.set_orb('conjunction', original_orb)
        assert astro_service.get_orb('conjunction') == original_orb
    
    def test_reload_config(self):
        """Тест перезагрузки конфигурации"""
        # Сохраняем текущие значения
        original_orbs = astro_service.ORBS
        
        # Изменяем вручную
        astro_service.set_orb('conjunction', 12.0)
        assert astro_service.get_orb('conjunction') == 12.0
        
        # Перезагружаем конфигурацию
        astro_service.reload_config()
        
        # Должны вернуться значения из конфигурации
        assert astro_service.get_orb('conjunction') == original_orbs['conjunction']
    
    def test_aspects_property(self):
        """Тест свойства ASPECTS"""
        aspects = astro_service.ASPECTS
        assert isinstance(aspects, list)
        assert len(aspects) > 0
        
        # Проверяем структуру
        for aspect in aspects:
            assert len(aspect) == 3
            assert isinstance(aspect[0], int)  # Угол
            assert isinstance(aspect[1], str)  # Название
            assert isinstance(aspect[2], str)  # Название на русском

