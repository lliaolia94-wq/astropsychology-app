"""
Сервис для работы с JWT токенами и аутентификацией
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database.models import User

logger = logging.getLogger(__name__)

# Настройки для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 минут
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 дней


class AuthService:
    """Сервис для работы с аутентификацией и JWT токенами"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Хеширование пароля"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Создание JWT access токена
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict) -> str:
        """
        Создание JWT refresh токена
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Проверка и декодирование JWT токена
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Проверяем тип токена
            if payload.get("type") != token_type:
                logger.warning(f"Неверный тип токена. Ожидается {token_type}")
                return None
            
            return payload
        except JWTError as e:
            logger.warning(f"Ошибка проверки токена: {str(e)}")
            return None

    @staticmethod
    def authenticate_user(db: Session, phone: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя по телефону и паролю
        """
        user = db.query(User).filter(User.phone == phone).first()
        
        if not user:
            logger.warning(f"Пользователь с телефоном {phone} не найден")
            return None
        
        if not AuthService.verify_password(password, user.password_hash):
            logger.warning(f"Неверный пароль для пользователя {phone}")
            return None
        
        if user.phone_verified != 1:
            logger.warning(f"Телефон пользователя {phone} не подтвержден")
            return None
        
        logger.info(f"Пользователь {phone} успешно аутентифицирован")
        return user

    @staticmethod
    def get_current_user(db: Session, token: str) -> Optional[User]:
        """
        Получение текущего пользователя по JWT токену
        """
        payload = AuthService.verify_token(token, token_type="access")
        if payload is None:
            return None
        
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user

