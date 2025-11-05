from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from database.database import get_db
from database.models import User
from services.auth_service import AuthService

router = APIRouter(tags=["General"])


@router.get("/", summary="Проверка работы API", description="Простой ответ для проверки, что сервис запущен")
async def root():
    return {"message": "Astropsychology API работает в PyCharm!", "status": "OK"}


@router.get("/health", summary="Проверка состояния сервиса и БД")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc)
    }


@router.post("/debug/check-user/{user_id}", summary="Проверить и создать пользователя (для отладки)")
async def check_and_create_user_debug(user_id: int, db: Session = Depends(get_db)):
    """Временный эндпоинт для проверки и создания пользователя с нужным ID"""
    # Проверяем пользователя с телефоном +79138817676
    phone = "+79138817676"
    user = db.query(User).filter(User.phone == phone).first()
    
    result = {
        "requested_user_id": user_id,
        "existing_user": None,
        "created": False,
        "all_users": []
    }
    
    # Показываем всех пользователей
    all_users = db.query(User).all()
    result["all_users"] = [
        {"id": u.id, "phone": u.phone, "name": u.name, "verified": u.phone_verified}
        for u in all_users
    ]
    
    if user:
        result["existing_user"] = {
            "id": user.id,
            "phone": user.phone,
            "name": user.name,
            "verified": user.phone_verified
        }
    
    # Проверяем, есть ли пользователь с нужным ID
    user_with_id = db.query(User).filter(User.id == user_id).first()
    if not user_with_id:
        # Создаем пользователя с нужным ID
        password_hash = AuthService.get_password_hash("SecurePass123")
        new_user = User(
            id=user_id,
            phone=f"{phone}_id{user_id}",
            password_hash=password_hash,
            phone_verified=1,
            name=f"Test User {user_id}"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        result["created"] = True
        result["created_user"] = {
            "id": new_user.id,
            "phone": new_user.phone,
            "name": new_user.name
        }
    
    return result


@router.post("/debug/test-token", summary="Тестировать токен (для отладки)")
async def test_token_debug(request: dict, db: Session = Depends(get_db)):
    token = request.get("token")
    """Временный эндпоинт для тестирования токена"""
    from jose import jwt
    from services.auth_service import SECRET_KEY, ALGORITHM
    
    result = {
        "token": token[:50] + "...",
        "secret_key": SECRET_KEY[:20] + "...",
        "decoded": None,
        "user_found": None,
        "error": None
    }
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        result["decoded"] = {
            "sub": payload.get("sub"),
            "type": payload.get("type"),
            "exp": payload.get("exp"),
            "sub_type": str(type(payload.get("sub")))
        }
        
        user_id = payload.get("sub")
        if user_id:
            user_id = int(user_id)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                result["user_found"] = {
                    "id": user.id,
                    "phone": user.phone,
                    "name": user.name
                }
            else:
                result["error"] = f"Пользователь с ID {user_id} не найден"
                
        # Тестируем через AuthService
        auth_user = AuthService.get_current_user(db, token)
        if auth_user:
            result["auth_service_user"] = {
                "id": auth_user.id,
                "phone": auth_user.phone
            }
        else:
            result["auth_service_error"] = "AuthService.get_current_user вернул None"
            
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
    
    return result


@router.post("/debug/apply-migration-004", summary="Применить миграцию 004 (для отладки)")
async def apply_migration_004(db: Session = Depends(get_db)):
    """Временный эндпоинт для применения миграции 004 - увеличение длины zodiac_sign"""
    try:
        from sqlalchemy import text
        
        # Увеличиваем длину zodiac_sign в PlanetPosition
        db.execute(text("""
            ALTER TABLE natal_charts_planetposition 
            ALTER COLUMN zodiac_sign TYPE VARCHAR(20);
        """))
        
        # Увеличиваем длину zodiac_sign в HouseCuspid
        db.execute(text("""
            ALTER TABLE natal_charts_housecuspid 
            ALTER COLUMN zodiac_sign TYPE VARCHAR(20);
        """))
        
        db.commit()
        
        return {
            "success": True,
            "message": "Миграция 004 применена успешно. Поля zodiac_sign увеличены до VARCHAR(20)"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

