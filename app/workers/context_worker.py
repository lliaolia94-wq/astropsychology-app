"""
Context Worker Service - фоновая обработка задач сохранения контекста
Запускается как отдельный процесс через RQ Worker
"""
import os
import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.models.database.models import ContextEntry, ChatSession
from app.services.vector_service import vector_service
from app.services.ai_service import DeepSeekAIChatService

load_dotenv()

logger = logging.getLogger(__name__)

# Инициализация БД для воркера
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Session:
    """Получение сессии БД для воркера"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        logger.error(f"Ошибка создания сессии БД: {str(e)}")
        db.close()
        raise


def structure_context_with_llm(
    user_message: str,
    ai_response: str
) -> Dict[str, Any]:
    """
    Структурирование контекста с помощью LLM
    
    Args:
        user_message: Сообщение пользователя
        ai_response: Ответ ИИ
        
    Returns:
        Словарь со структурированными данными
    """
    try:
        ai_service = DeepSeekAIChatService()
        
        # Промпт для структурирования
        structure_prompt = f"""
Проанализируй следующий диалог и извлеки структурированную информацию:

Сообщение пользователя: {user_message}
Ответ ИИ: {ai_response}

Верни JSON с полями:
- emotional_state: эмоциональное состояние пользователя (радость, грусть, злость, страх, удивление, спокойствие, тревога, напряжение)
- event_description: описание события или ситуации (если есть)
- insight_text: ключевой инсайт или понимание (если есть)
- tags: список тегов (максимум 5 тегов, например: ["работа", "отношения", "здоровье", "финансы", "духовность", "астрология"])
- priority: приоритет записи от 1 до 5 (5 - критически важно, 1 - обычная запись)

Если какого-то поля нет, верни null для него.
"""
        
        response = ai_service.chat_sync(structure_prompt)
        
        # Пытаемся извлечь JSON из ответа
        import json
        import re
        
        # Ищем JSON в ответе
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                structured = json.loads(json_match.group())
                return structured
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON из ответа LLM")
        
        # Если не удалось распарсить, возвращаем базовую структуру
        return {
            "emotional_state": None,
            "event_description": None,
            "insight_text": None,
            "tags": [],
            "priority": 1
        }
    except Exception as e:
        logger.error(f"Ошибка структурирования через LLM: {str(e)}")
        return {
            "emotional_state": None,
            "event_description": None,
            "insight_text": None,
            "tags": [],
            "priority": 1
        }


def process_context_save_task(
    session_id: int,
    user_id: int,
    user_message: str,
    ai_response: str,
    trigger_type: str = "message_count",
    astro_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Обработка задачи сохранения контекста
    
    Эта функция вызывается RQ Worker'ом
    
    Args:
        session_id: ID сессии
        user_id: ID пользователя
        user_message: Сообщение пользователя
        ai_response: Ответ ИИ
        trigger_type: Тип триггера (message_count, timeout, manual, critical)
        astro_context: Астрологический контекст (опционально)
        
    Returns:
        Словарь с результатом обработки
    """
    db = get_db_session()
    
    try:
        logger.info(f"Начало обработки задачи сохранения контекста для сессии {session_id}")
        
        # Проверяем существование сессии
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            logger.error(f"Сессия {session_id} не найдена")
            return {"success": False, "error": "Session not found"}
        
        # Структурируем контекст через LLM
        structured_data = structure_context_with_llm(user_message, ai_response)
        
        # Создаем контекстную запись
        context_entry = ContextEntry(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            ai_response=ai_response,
            emotional_state=structured_data.get("emotional_state"),
            event_description=structured_data.get("event_description"),
            insight_text=structured_data.get("insight_text"),
            tags=structured_data.get("tags", []),
            priority=structured_data.get("priority", 1),
            entry_type=trigger_type,
            astro_context=astro_context
        )
        
        db.add(context_entry)
        db.commit()
        db.refresh(context_entry)
        
        logger.info(f"✅ Контекстная запись создана: {context_entry.id}")
        
        # Создаем векторное представление
        vector_id = str(uuid.uuid4())
        
        # Комбинированный текст для семантического поиска
        combined_text = f"{user_message}\n{ai_response}"
        if structured_data.get("event_description"):
            combined_text += f"\n{structured_data['event_description']}"
        if structured_data.get("insight_text"):
            combined_text += f"\n{structured_data['insight_text']}"
        
        # Payload для Qdrant
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "entry_id": context_entry.id,
            "tags": structured_data.get("tags", []),
            "priority": structured_data.get("priority", 1),
            "emotional_state": structured_data.get("emotional_state"),
            "entry_type": trigger_type
        }
        
        # Сохраняем вектор
        vector_saved = vector_service.save_vector(
            vector_id=vector_id,
            text=combined_text,
            payload=payload
        )
        
        if vector_saved:
            # Обновляем запись с vector_id
            context_entry.vector_id = vector_id
            db.commit()
            logger.info(f"✅ Вектор сохранен в Qdrant: {vector_id}")
        else:
            logger.warning(f"⚠️ Не удалось сохранить вектор для записи {context_entry.id}")
        
        # Инвалидируем кеш сессии
        from app.services.redis_service import redis_service
        redis_service.invalidate_session_context(session_id)
        
        return {
            "success": True,
            "entry_id": context_entry.id,
            "vector_id": vector_id if vector_saved else None
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки задачи сохранения контекста: {str(e)}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# Функция для прямого вызова (без RQ) - для тестирования
def save_context_sync(
    session_id: int,
    user_id: int,
    user_message: str,
    ai_response: str,
    trigger_type: str = "message_count",
    astro_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Синхронное сохранение контекста (для тестирования или прямого вызова)
    """
    return process_context_save_task(
        session_id=session_id,
        user_id=user_id,
        user_message=user_message,
        ai_response=ai_response,
        trigger_type=trigger_type,
        astro_context=astro_context
    )

