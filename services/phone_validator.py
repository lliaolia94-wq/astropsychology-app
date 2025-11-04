"""
Утилиты для валидации телефонных номеров
"""
import re
from typing import Tuple, Optional


class PhoneValidator:
    """Валидатор телефонных номеров"""
    
    # Паттерны для разных стран
    COUNTRY_PATTERNS = {
        "+7": r"^\+7\d{10}$",  # Россия: +7XXXXXXXXXX (10 цифр после +7)
        "+1": r"^\+1\d{10}$",  # США/Канада
        "+44": r"^\+44\d{10}$",  # Великобритания
        "+49": r"^\+49\d{10,11}$",  # Германия
    }
    
    DEFAULT_COUNTRY = "+7"  # Россия по умолчанию

    @staticmethod
    def normalize_phone(phone: str, country_code: str = None) -> Optional[str]:
        """
        Нормализация номера телефона
        Удаляет все символы кроме цифр и +, добавляет код страны если нужно
        """
        # Удаляем все символы кроме цифр и +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Если номер не начинается с +, добавляем код страны
        if not cleaned.startswith('+'):
            country_code = country_code or PhoneValidator.DEFAULT_COUNTRY
            # Удаляем ведущий 0 если есть
            if cleaned.startswith('0'):
                cleaned = cleaned[1:]
            cleaned = country_code + cleaned
        
        return cleaned

    @staticmethod
    def validate_phone(phone: str, country_code: str = None) -> Tuple[bool, Optional[str]]:
        """
        Валидация номера телефона
        Возвращает (is_valid, normalized_phone)
        """
        normalized = PhoneValidator.normalize_phone(phone, country_code)
        
        if not normalized:
            return False, None
        
        # Определяем код страны
        country_code = normalized[:2] if normalized.startswith('+7') else normalized[:3]
        
        # Проверяем паттерн
        pattern = PhoneValidator.COUNTRY_PATTERNS.get(country_code)
        if pattern and re.match(pattern, normalized):
            return True, normalized
        
        # Если паттерна нет, проверяем базовую структуру
        if normalized.startswith('+') and len(normalized) >= 10:
            return True, normalized
        
        return False, None

    @staticmethod
    def format_phone_display(phone: str) -> str:
        """
        Форматирование номера для отображения
        Пример: +79161234567 -> +7 (916) 123-45-67
        """
        if phone.startswith('+7') and len(phone) == 12:
            # Россия: +7 (XXX) XXX-XX-XX
            return f"+7 ({phone[2:5]}) {phone[5:8]}-{phone[8:10]}-{phone[10:12]}"
        return phone

