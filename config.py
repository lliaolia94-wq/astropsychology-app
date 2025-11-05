"""
Конфигурация для астрологических расчетов.
Орбисы аспектов и другие настройки можно изменять через переменные окружения.
"""
import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


class AstrologyConfig:
    """Конфигурация для астрологических расчетов"""
    
    # Орбисы аспектов (профессиональный стандарт)
    # Можно переопределить через переменные окружения
    DEFAULT_ORBS = {
        'conjunction': 8.0,
        'opposition': 8.0,
        'trine': 8.0,
        'square': 8.0,
        'sextile': 6.0,
        # Дополнительные аспекты (для будущего расширения)
        'quincunx': 3.0,
        'semisextile': 2.0,
    }
    
    @classmethod
    def get_orbs(cls) -> Dict[str, float]:
        """
        Получает орбисы аспектов.
        Приоритет: переменные окружения > значения по умолчанию
        
        Переменные окружения:
        - ASPECT_ORB_CONJUNCTION
        - ASPECT_ORB_OPPOSITION
        - ASPECT_ORB_TRINE
        - ASPECT_ORB_SQUARE
        - ASPECT_ORB_SEXTILE
        - ASPECT_ORB_QUINCUNX
        - ASPECT_ORB_SEMISEXTILE
        """
        orbs = cls.DEFAULT_ORBS.copy()
        
        # Переопределяем через переменные окружения
        for aspect_name in orbs.keys():
            env_key = f"ASPECT_ORB_{aspect_name.upper()}"
            env_value = os.getenv(env_key)
            if env_value:
                try:
                    orbs[aspect_name] = float(env_value)
                except ValueError:
                    print(f"⚠️ Неверное значение для {env_key}: {env_value}. Используется значение по умолчанию.")
        
        return orbs
    
    @classmethod
    def get_orb(cls, aspect_name: str) -> float:
        """
        Получает орбис для конкретного аспекта.
        
        Args:
            aspect_name: Название аспекта ('conjunction', 'square', etc.)
            
        Returns:
            Орбис в градусах
        """
        orbs = cls.get_orbs()
        return orbs.get(aspect_name, 0.0)
    
    # Аспекты с их углами (константы)
    ASPECTS = [
        (0, 'conjunction', 'соединение'),
        (60, 'sextile', 'секстиль'),
        (90, 'square', 'квадрат'),
        (120, 'trine', 'трин'),
        (180, 'opposition', 'оппозиция'),
        # Дополнительные аспекты (для будущего расширения)
        # (30, 'semisextile', 'полусекстиль'),
        # (150, 'quincunx', 'квинконс'),
    ]
    
    # Системы домов по умолчанию
    DEFAULT_HOUSES_SYSTEM = os.getenv('DEFAULT_HOUSES_SYSTEM', 'placidus')
    
    # Тип зодиака по умолчанию
    DEFAULT_ZODIAC_TYPE = os.getenv('DEFAULT_ZODIAC_TYPE', 'tropical')
    
    # Минимальный орбис для учета аспекта (можно настроить)
    MIN_ORB_THRESHOLD = float(os.getenv('MIN_ORB_THRESHOLD', '0.0'))


# Глобальный экземпляр конфигурации
config = AstrologyConfig()

