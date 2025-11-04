"""
Сервис для ограничения частоты запросов (Rate Limiting)
Защита от брутфорса
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Простой in-memory rate limiter"""
    
    # Хранение запросов: {phone: [timestamp1, timestamp2, ...]}
    _requests: Dict[str, list] = defaultdict(list)
    
    # Ограничения
    SMS_REQUESTS_PER_HOUR = 5  # Максимум 5 запросов SMS в час
    LOGIN_ATTEMPTS_PER_HOUR = 5  # Максимум 5 попыток входа в час
    CODE_VERIFY_ATTEMPTS_PER_HOUR = 10  # Максимум 10 попыток проверки кода в час

    @classmethod
    def _cleanup_old_requests(cls, phone: str, window_minutes: int = 60):
        """Удаление старых запросов"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        cls._requests[phone] = [
            ts for ts in cls._requests[phone] if ts > cutoff
        ]

    @classmethod
    def check_sms_rate_limit(cls, phone: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка ограничения на отправку SMS
        Возвращает (allowed, error_message)
        """
        cls._cleanup_old_requests(phone, window_minutes=60)
        
        if len(cls._requests[phone]) >= cls.SMS_REQUESTS_PER_HOUR:
            logger.warning(f"Превышен лимит SMS запросов для {phone}")
            return False, f"Превышен лимит запросов. Попробуйте через час."
        
        cls._requests[phone].append(datetime.now(timezone.utc))
        return True, None

    @classmethod
    def check_login_rate_limit(cls, phone: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка ограничения на попытки входа
        """
        cls._cleanup_old_requests(phone, window_minutes=60)
        
        if len(cls._requests[phone]) >= cls.LOGIN_ATTEMPTS_PER_HOUR:
            logger.warning(f"Превышен лимит попыток входа для {phone}")
            return False, f"Превышен лимит попыток входа. Попробуйте через час."
        
        cls._requests[phone].append(datetime.now(timezone.utc))
        return True, None

    @classmethod
    def check_code_verify_rate_limit(cls, phone: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка ограничения на проверку кодов
        """
        cls._cleanup_old_requests(phone, window_minutes=60)
        
        if len(cls._requests[phone]) >= cls.CODE_VERIFY_ATTEMPTS_PER_HOUR:
            logger.warning(f"Превышен лимит проверок кода для {phone}")
            return False, f"Превышен лимит проверок кода. Попробуйте через час."
        
        cls._requests[phone].append(datetime.now(timezone.utc))
        return True, None

    @classmethod
    def reset_limits(cls, phone: str):
        """Сброс лимитов для телефона (например, после успешной аутентификации)"""
        if phone in cls._requests:
            del cls._requests[phone]
            logger.info(f"Лимиты сброшены для {phone}")

