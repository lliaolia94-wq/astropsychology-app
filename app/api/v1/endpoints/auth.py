"""
Роутер для аутентификации пользователей
"""
import re
import logging
import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.models.database.models import User
from app.models.schemas.schemas import (
    PhoneRequest,
    SMSVerifyRequest,
    PasswordSetRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    MessageResponse,
    UserAuthResponse
)
from app.services.sms_service import SMSService
from app.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.phone_validator import PhoneValidator
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Пользователь"])
security = HTTPBearer()


def validate_password(password: str) -> bool:
    """
    Валидация пароля: минимум 8 символов, буквы и цифры
    """
    if len(password) < 8:
        return False
    if not re.search(r'[a-zA-Zа-яА-Я]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость для получения текущего пользователя из JWT токена
    """
    token = credentials.credentials
    
    user = AuthService.get_current_user(db, token)
    if user is None:
        # Проверяем, может быть это refresh токен, чтобы дать более понятное сообщение
        try:
            from jose import jwt
            from app.services.auth_service import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_type = payload.get("type")
            user_id_from_token = payload.get("sub")
            
            if token_type == "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Использован refresh токен. Для этого эндпоинта требуется access токен. Используйте токен из поля 'access_token' ответа /auth/login",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Если токен валиден, но пользователь не найден, проверяем в базе
            if user_id_from_token:
                user_id_from_token = int(user_id_from_token)
                user_check = db.query(User).filter(User.id == user_id_from_token).first()
                if not user_check:
                    logger.error(f"Пользователь с ID {user_id_from_token} из токена не найден в базе данных")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Пользователь с ID {user_id_from_token} не найден в базе данных. Возможно, учетная запись была удалена.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Ошибка при проверке токена: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший токен. Убедитесь, что используете access токен, а не refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post(
    "/auth/send-sms",
    response_model=MessageResponse,
    summary="Отправить SMS-код подтверждения"
)
async def send_sms_code(
    request: PhoneRequest,
    db: Session = Depends(get_db)
):
    """
    Отправка SMS-кода на номер телефона для регистрации или восстановления пароля
    """
    # Валидация и нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(
        request.phone,
        request.country_code
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка rate limit
    allowed, error_msg = RateLimiter.check_sms_rate_limit(normalized_phone)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg
        )
    
    # Создание и отправка кода
    sms_code = SMSService.create_and_send_code(db, normalized_phone)
    
    if sms_code is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отправить SMS-код. Попробуйте позже"
        )
    
    logger.info(f"SMS код отправлен на {normalized_phone}")
    return MessageResponse(message="SMS-код отправлен на указанный номер")


@router.post(
    "/auth/verify-sms",
    response_model=MessageResponse,
    summary="Подтвердить SMS-код"
)
async def verify_sms_code(
    request: SMSVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Подтверждение SMS-кода. После успешного подтверждения можно устанавливать пароль
    """
    # Нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(request.phone)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка rate limit
    allowed, error_msg = RateLimiter.check_code_verify_rate_limit(normalized_phone)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg
        )
    
    # Проверка кода
    if not SMSService.verify_code(db, normalized_phone, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код или истек срок действия"
        )
    
    logger.info(f"SMS код подтвержден для {normalized_phone}")
    return MessageResponse(message="Код успешно подтвержден")


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    summary="Регистрация пользователя"
)
async def register_user(
    request: PasswordSetRequest,
    db: Session = Depends(get_db)
):
    """
    Регистрация пользователя: установка пароля после подтверждения SMS-кода
    """
    # Нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(request.phone)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка существования пользователя
    existing_user = db.query(User).filter(User.phone == normalized_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким номером телефона уже зарегистрирован"
        )
    
    # Валидация пароля
    if not validate_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать минимум 8 символов, буквы и цифры"
        )
    
    # Проверка совпадения паролей
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )
    
    # Проверка подтверждения SMS-кода (код должен быть использован)
    # ВРЕМЕННАЯ ЗАГЛУШКА: Можно отключить проверку SMS через переменную окружения SKIP_SMS_VERIFICATION=true
    skip_sms_check = os.getenv("SKIP_SMS_VERIFICATION", "false").lower() == "true"
    
    if not skip_sms_check:
        from app.models.database.models import SMSCode
        sms_code = db.query(SMSCode).filter(
            SMSCode.phone == normalized_phone,
            SMSCode.used == 1
        ).order_by(SMSCode.created_at.desc()).first()
        
        if not sms_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сначала подтвердите SMS-код"
            )
    else:
        logger.warning(f"⚠️ ПРОВЕРКА SMS ОТКЛЮЧЕНА (тестовый режим). Регистрация пользователя {normalized_phone} без проверки SMS-кода")
    
    # Создание пользователя
    password_hash = AuthService.get_password_hash(request.password)
    user = User(
        phone=normalized_phone,
        password_hash=password_hash,
        phone_verified=1,
        name="",  # Устанавливаем пустую строку, так как name может быть NOT NULL в БД
        birth_date="",  # Устанавливаем пустую строку для полей, которые могут быть NOT NULL
        birth_time="",
        birth_place=""
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Генерация токенов
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id)},  # JWT требует, чтобы sub был строкой
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id)})  # JWT требует, чтобы sub был строкой
    
    logger.info(f"Пользователь {normalized_phone} успешно зарегистрирован")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Вход в систему"
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Аутентификация пользователя по номеру телефона и паролю
    """
    # Нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(request.phone)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка rate limit
    allowed, error_msg = RateLimiter.check_login_rate_limit(normalized_phone)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg
        )
    
    # Аутентификация
    user = AuthService.authenticate_user(db, normalized_phone, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный номер телефона или пароль"
        )
    
    # Сброс лимитов при успешной аутентификации
    RateLimiter.reset_limits(normalized_phone)
    
    # Генерация токенов
    logger.info(f"Создаю токены для пользователя: ID={user.id}, phone={user.phone}, type(user.id)={type(user.id)}")
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id)},  # JWT требует, чтобы sub был строкой
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id)})  # JWT требует, чтобы sub был строкой
    
    logger.info(f"Пользователь {normalized_phone} успешно вошел в систему. Access token создан: {access_token[:50]}...")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Обновить токен"
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Обновление access токена с помощью refresh токена
    """
    # Проверка refresh токена
    payload = AuthService.verify_token(request.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший refresh токен"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    # Генерация новых токенов
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id)},  # JWT требует, чтобы sub был строкой
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id)})  # JWT требует, чтобы sub был строкой
    
    logger.info(f"Токены обновлены для пользователя {user.phone}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    summary="Сброс пароля (запрос SMS-кода)"
)
async def reset_password_request(
    request: PhoneRequest,
    db: Session = Depends(get_db)
):
    """
    Запрос на сброс пароля. Отправляет SMS-код на номер телефона
    """
    # Нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(
        request.phone,
        request.country_code
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка существования пользователя
    user = db.query(User).filter(User.phone == normalized_phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким номером телефона не найден"
        )
    
    # Проверка rate limit
    allowed, error_msg = RateLimiter.check_sms_rate_limit(normalized_phone)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg
        )
    
    # Отправка SMS-кода
    sms_code = SMSService.create_and_send_code(db, normalized_phone)
    if sms_code is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отправить SMS-код. Попробуйте позже"
        )
    
    logger.info(f"SMS код для сброса пароля отправлен на {normalized_phone}")
    return MessageResponse(message="SMS-код для сброса пароля отправлен")


@router.post(
    "/auth/reset-password-confirm",
    response_model=MessageResponse,
    summary="Подтверждение сброса пароля"
)
async def reset_password_confirm(
    request: PasswordSetRequest,
    db: Session = Depends(get_db)
):
    """
    Установка нового пароля после подтверждения SMS-кода
    """
    # Нормализация телефона
    is_valid, normalized_phone = PhoneValidator.validate_phone(request.phone)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат номера телефона"
        )
    
    # Проверка существования пользователя
    user = db.query(User).filter(User.phone == normalized_phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверка подтверждения SMS-кода
    # ВРЕМЕННАЯ ЗАГЛУШКА: Можно отключить проверку SMS через переменную окружения SKIP_SMS_VERIFICATION=true
    skip_sms_check = os.getenv("SKIP_SMS_VERIFICATION", "false").lower() == "true"
    
    if not skip_sms_check:
        from app.models.database.models import SMSCode
        sms_code = db.query(SMSCode).filter(
            SMSCode.phone == normalized_phone,
            SMSCode.used == 1
        ).order_by(SMSCode.created_at.desc()).first()
        
        if not sms_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сначала подтвердите SMS-код"
            )
    else:
        logger.warning(f"⚠️ ПРОВЕРКА SMS ОТКЛЮЧЕНА (тестовый режим). Сброс пароля для {normalized_phone} без проверки SMS-кода")
    
    # Валидация пароля
    if not validate_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать минимум 8 символов, буквы и цифры"
        )
    
    # Проверка совпадения паролей
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )
    
    # Обновление пароля
    user.password_hash = AuthService.get_password_hash(request.password)
    db.commit()
    
    logger.info(f"Пароль успешно сброшен для пользователя {normalized_phone}")
    return MessageResponse(message="Пароль успешно изменен")


@router.get(
    "/auth/me",
    response_model=UserAuthResponse,
    summary="Получить информацию о текущем пользователе"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о текущем аутентифицированном пользователе
    """
    return UserAuthResponse(
        id=current_user.id,
        phone=current_user.phone,
        phone_verified=bool(current_user.phone_verified),
        name=current_user.name
    )


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    summary="Выход из системы"
)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Выход из системы (в текущей реализации просто подтверждает выход)
    TODO: Реализовать blacklist токенов при необходимости
    """
    logger.info(f"Пользователь {current_user.phone} вышел из системы")
    return MessageResponse(message="Успешный выход из системы")

