"""
Сервис для работы с SMS-кодами подтверждения
"""
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from database.models import SMSCode

logger = logging.getLogger(__name__)


class SMSService:
    """Сервис для отправки и проверки SMS-кодов"""
    
    CODE_LENGTH = 6  # Длина кода (4-6 символов)
    CODE_EXPIRY_MINUTES = 5  # Срок действия кода в минутах
    MAX_ATTEMPTS = 5  # Максимальное количество попыток ввода

    @staticmethod
    def generate_code() -> str:
        """Генерация случайного числового кода"""
        return str(random.randint(10**(SMSService.CODE_LENGTH-1), 10**SMSService.CODE_LENGTH - 1))

    @staticmethod
    def send_sms(phone: str, code: str) -> bool:
        """
        Отправка SMS-кода на телефон
        TODO: Интегрировать с реальным SMS-провайдером (SMS.ru, Twilio, etc.)
        В DEV режиме просто логируем код
        """
        try:
            # TODO: Интеграция с реальным SMS-провайдером
            # Пример: SMS.ru API
            # response = requests.post(
            #     "https://sms.ru/sms/send",
            #     data={
            #         "api_id": os.getenv("SMS_API_KEY"),
            #         "to": phone,
            #         "msg": f"Ваш код подтверждения: {code}"
            #     }
            # )
            
            # В DEV режиме просто логируем
            logger.info(f"[DEV] SMS код для {phone}: {code}")
            print(f"[DEV] SMS код для {phone}: {code}")  # Для удобства разработки
            
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки SMS на {phone}: {str(e)}")
            return False

    @staticmethod
    def create_and_send_code(db: Session, phone: str) -> Optional[SMSCode]:
        """
        Создание и отправка SMS-кода
        Помечает старые коды как использованные
        """
        # Помечаем старые коды как использованные
        db.query(SMSCode).filter(
            SMSCode.phone == phone,
            SMSCode.used == 0
        ).update({"used": 1})
        db.commit()

        # Генерируем новый код
        code = SMSService.generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=SMSService.CODE_EXPIRY_MINUTES)

        # Создаем запись в БД
        sms_code = SMSCode(
            phone=phone,
            code=code,
            expires_at=expires_at,
            attempts=0,
            used=0
        )
        db.add(sms_code)
        db.commit()
        db.refresh(sms_code)

        # Отправляем SMS
        if SMSService.send_sms(phone, code):
            logger.info(f"SMS код создан и отправлен для {phone}")
            return sms_code
        else:
            # Если отправка не удалась, удаляем запись
            db.delete(sms_code)
            db.commit()
            return None

    @staticmethod
    def verify_code(db: Session, phone: str, code: str) -> bool:
        """
        Проверка SMS-кода
        Возвращает True если код верный и не истек
        """
        # Находим последний неиспользованный код для этого телефона
        sms_code = db.query(SMSCode).filter(
            SMSCode.phone == phone,
            SMSCode.used == 0,
            SMSCode.expires_at > datetime.now(timezone.utc)
        ).order_by(SMSCode.created_at.desc()).first()

        if not sms_code:
            logger.warning(f"Код не найден или истек для {phone}")
            return False

        # Проверяем количество попыток
        if sms_code.attempts >= SMSService.MAX_ATTEMPTS:
            logger.warning(f"Превышено количество попыток для {phone}")
            sms_code.used = 1  # Помечаем как использованный
            db.commit()
            return False

        # Увеличиваем счетчик попыток
        sms_code.attempts += 1

        # Проверяем код
        if sms_code.code == code:
            sms_code.used = 1  # Помечаем как использованный
            db.commit()
            logger.info(f"Код успешно подтвержден для {phone}")
            return True
        else:
            db.commit()
            logger.warning(f"Неверный код для {phone}. Попытка {sms_code.attempts}/{SMSService.MAX_ATTEMPTS}")
            return False

    @staticmethod
    def cleanup_expired_codes(db: Session):
        """Очистка истекших кодов (можно вызывать периодически)"""
        expired_count = db.query(SMSCode).filter(
            SMSCode.expires_at < datetime.now(timezone.utc)
        ).update({"used": 1})
        db.commit()
        if expired_count > 0:
            logger.info(f"Очищено {expired_count} истекших SMS-кодов")

