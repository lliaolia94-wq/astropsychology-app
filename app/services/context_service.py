"""
Сервис для управления контекстом общения
Логика определения сессий, триггеры сохранения, интеграция с векторным поиском
"""
import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.database.models import ChatSession, ContextEntry, ChatMessage
from app.services.vector_service import vector_service
from app.services.redis_service import redis_service
from app.services.ai_service import DeepSeekAIChatService

logger = logging.getLogger(__name__)


class ContextService:
    """Сервис для управления контекстом общения"""
    
    # Константы из ТЗ
    SESSION_TIMEOUT_HOURS = 4  # 4 часа бездействия
    MESSAGE_COUNT_TRIGGER = 5  # Каждые 5 сообщений
    INACTIVITY_TIMEOUT_MINUTES = 30  # 30 минут бездействия
    
    # Ключевые слова для смены темы (создание новой сессии)
    TOPIC_CHANGE_KEYWORDS = [
        'экстренная помощь', 'экстрен', 'критично', 'срочно',
        'принятие решения', 'решение', 'выбор',
        'новая тема', 'другое', 'переключись'
    ]
    
    # Критические шаблоны
    CRITICAL_TEMPLATES = ['emergency', 'decision', 'критично']
    
    def __init__(self):
        self.ai_service = DeepSeekAIChatService()
    
    # ============ Управление сессиями ============
    
    def get_or_create_active_session(
        self,
        db: Session,
        user_id: int,
        template_type: Optional[str] = None,
        force_new: bool = False
    ) -> ChatSession:
        """
        Получение активной сессии или создание новой
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            template_type: Тип шаблона (для определения типа сессии)
            force_new: Принудительное создание новой сессии
            
        Returns:
            Объект ChatSession
        """
        if force_new:
            return self._create_new_session(db, user_id, template_type)
        
        # Ищем активную сессию
        active_session = db.query(ChatSession).filter(
            and_(
                ChatSession.user_id == user_id,
                ChatSession.is_active == 1
            )
        ).order_by(ChatSession.updated_at.desc()).first()
        
        if active_session:
            # Проверяем время бездействия
            now = datetime.now(timezone.utc)
            updated_at = active_session.updated_at
            # Нормализуем updated_at к timezone-aware, если он naive
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            time_since_update = now - updated_at
            
            if time_since_update < timedelta(hours=self.SESSION_TIMEOUT_HOURS):
                # Сессия активна, обновляем время
                active_session.updated_at = datetime.now(timezone.utc)
                db.commit()
                return active_session
            else:
                # Сессия истекла, деактивируем
                active_session.is_active = 0
                db.commit()
        
        # Создаем новую сессию
        return self._create_new_session(db, user_id, template_type)
    
    def _create_new_session(
        self,
        db: Session,
        user_id: int,
        template_type: Optional[str] = None
    ) -> ChatSession:
        """
        Создание новой сессии общения
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            template_type: Тип шаблона
            
        Returns:
            Объект ChatSession
        """
        # Определяем тип сессии
        session_type = 'regular'
        if template_type in ['emergency', 'критично']:
            session_type = 'emergency'
        elif template_type in ['decision', 'решение']:
            session_type = 'decision'
        
        # Генерируем заголовок через LLM (пока заглушка)
        title = f"Сессия {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        
        # TODO: Генерация заголовка через LLM
        # title = self._generate_session_title(db, user_id, template_type)
        
        new_session = ChatSession(
            user_id=user_id,
            title=title,
            template_type=template_type,
            session_type=session_type,
            is_active=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"✅ Создана новая сессия {new_session.id} для пользователя {user_id}")
        return new_session
    
    def _generate_session_title(
        self,
        db: Session,
        user_id: int,
        template_type: Optional[str] = None
    ) -> str:
        """
        Генерация заголовка сессии через LLM
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            template_type: Тип шаблона
            
        Returns:
            Заголовок сессии
        """
        try:
            # Получаем последние сообщения для контекста
            last_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id.in_(
                    db.query(ChatSession.id).filter(ChatSession.user_id == user_id)
                )
            ).order_by(ChatMessage.timestamp.desc()).limit(3).all()
            
            context = ""
            if last_messages:
                context = "\n".join([msg.content for msg in reversed(last_messages)])
            
            prompt = f"""
На основе следующего контекста создай короткий заголовок (до 50 символов) для новой сессии общения:

Контекст:
{context}

Тип шаблона: {template_type or 'обычный'}

Заголовок должен отражать суть разговора. Верни только заголовок, без дополнительных слов.
"""
            
            title = self.ai_service.chat_sync(prompt)
            # Очищаем заголовок от лишних символов
            title = title.strip().strip('"').strip("'")[:50]
            return title if title else f"Сессия {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        except Exception as e:
            logger.error(f"Ошибка генерации заголовка: {str(e)}")
            return f"Сессия {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    
    def check_session_timeout(self, db: Session, session_id: int) -> bool:
        """
        Проверка истекла ли сессия по времени
        
        Args:
            db: Сессия БД
            session_id: ID сессии
            
        Returns:
            True если сессия истекла
        """
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return True
        
        now = datetime.now(timezone.utc)
        # Нормализуем updated_at к timezone-aware, если он naive
        updated_at = session.updated_at
        if updated_at.tzinfo is None:
            # Если datetime naive, предполагаем UTC
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        time_since_update = now - updated_at
        return time_since_update >= timedelta(hours=self.SESSION_TIMEOUT_HOURS)
    
    def check_topic_change(self, message: str) -> bool:
        """
        Проверка наличия ключевых слов для смены темы
        
        Args:
            message: Сообщение пользователя
            
        Returns:
            True если нужно создать новую сессию
        """
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.TOPIC_CHANGE_KEYWORDS)
    
    # ============ Триггеры сохранения контекста ============
    
    def should_save_context(
        self,
        db: Session,
        session_id: int,
        user_message: str,
        message_count: int
    ) -> Tuple[bool, str]:
        """
        Определение необходимости сохранения контекста
        
        Args:
            db: Сессия БД
            session_id: ID сессии
            user_message: Сообщение пользователя
            message_count: Количество сообщений в сессии
            
        Returns:
            Кортеж (should_save, trigger_type)
        """
        # Обязательные триггеры
        
        # 1. Каждые 5 сообщений
        if message_count > 0 and message_count % self.MESSAGE_COUNT_TRIGGER == 0:
            return True, "message_count"
        
        # 2. Превышение 30 минут бездействия
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            now = datetime.now(timezone.utc)
            updated_at = session.updated_at
            # Нормализуем updated_at к timezone-aware, если он naive
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            time_since_update = now - updated_at
            if time_since_update >= timedelta(minutes=self.INACTIVITY_TIMEOUT_MINUTES):
                return True, "timeout"
        
        # 3. Критические шаблоны
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session and session.template_type in self.CRITICAL_TEMPLATES:
            return True, "critical"
        
        # Опциональные триггеры (через LLM анализ)
        # TODO: Реализовать LLM анализ для определения важности
        # Пока пропускаем для производительности
        
        return False, ""
    
    # ============ Получение релевантного контекста ============
    
    def get_relevant_context(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        current_message: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получение релевантного контекста для промпта
        
        Согласно ТЗ:
        - 3 последние записи из текущей сессии
        - 5 семантически близких записей из истории
        - Все критически важные записи за 30 дней
        
        Args:
            db: Сессия БД
            session_id: ID текущей сессии
            user_id: ID пользователя
            current_message: Текущее сообщение (для семантического поиска)
            limit: Максимальное количество записей
            
        Returns:
            Список релевантных контекстных записей
        """
        results = []
        
        # 1. 3 последние записи из текущей сессии
        recent_session_entries = db.query(ContextEntry).filter(
            and_(
                ContextEntry.session_id == session_id,
                ContextEntry.user_id == user_id
            )
        ).order_by(ContextEntry.created_at.desc()).limit(3).all()
        
        for entry in recent_session_entries:
            results.append({
                'id': entry.id,
                'user_message': entry.user_message,
                'ai_response': entry.ai_response,
                'emotional_state': entry.emotional_state,
                'event_description': entry.event_description,
                'insight_text': entry.insight_text,
                'tags': entry.tags,
                'priority': entry.priority,
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
                'source': 'current_session'
            })
        
        # 2. Семантически близкие записи через векторный поиск
        if current_message and vector_service.client:
            vector_results = vector_service.search_similar(
                query_text=current_message,
                user_id=user_id,
                limit=5,
                score_threshold=0.6
            )
            
            for result in vector_results:
                entry_id = result['payload'].get('entry_id')
                if entry_id:
                    entry = db.query(ContextEntry).filter(
                        ContextEntry.id == entry_id
                    ).first()
                    
                    if entry and entry.id not in [r['id'] for r in results]:
                        results.append({
                            'id': entry.id,
                            'user_message': entry.user_message,
                            'ai_response': entry.ai_response,
                            'emotional_state': entry.emotional_state,
                            'event_description': entry.event_description,
                            'insight_text': entry.insight_text,
                            'tags': entry.tags,
                            'priority': entry.priority,
                            'created_at': entry.created_at.isoformat() if entry.created_at else None,
                            'similarity_score': result['score'],
                            'source': 'semantic_search'
                        })
        
        # 3. Критически важные записи за 30 дней
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        critical_entries = db.query(ContextEntry).filter(
            and_(
                ContextEntry.user_id == user_id,
                ContextEntry.priority >= 4,
                ContextEntry.created_at >= thirty_days_ago
            )
        ).order_by(ContextEntry.priority.desc(), ContextEntry.created_at.desc()).limit(10).all()
        
        for entry in critical_entries:
            if entry.id not in [r['id'] for r in results]:
                results.append({
                    'id': entry.id,
                    'user_message': entry.user_message,
                    'ai_response': entry.ai_response,
                    'emotional_state': entry.emotional_state,
                    'event_description': entry.event_description,
                    'insight_text': entry.insight_text,
                    'tags': entry.tags,
                    'priority': entry.priority,
                    'created_at': entry.created_at.isoformat() if entry.created_at else None,
                    'source': 'critical_important'
                })
        
        # Убираем дубликаты и ограничиваем количество
        seen_ids = set()
        unique_results = []
        for result in results:
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                unique_results.append(result)
                if len(unique_results) >= limit:
                    break
        
        return unique_results
    
    def format_context_for_prompt(
        self,
        context_entries: List[Dict[str, Any]]
    ) -> str:
        """
        Форматирование контекста для промпта LLM
        
        Args:
            context_entries: Список контекстных записей
            
        Returns:
            Отформатированный текст для промпта
        """
        if not context_entries:
            return ""
        
        formatted = "\n\n=== РЕЛЕВАНТНЫЙ КОНТЕКСТ ИЗ ИСТОРИИ ===\n"
        
        for i, entry in enumerate(context_entries, 1):
            formatted += f"\n--- Запись {i} ---\n"
            if entry.get('user_message'):
                formatted += f"Пользователь: {entry['user_message']}\n"
            if entry.get('ai_response'):
                formatted += f"ИИ: {entry['ai_response']}\n"
            if entry.get('emotional_state'):
                formatted += f"Эмоция: {entry['emotional_state']}\n"
            if entry.get('event_description'):
                formatted += f"Событие: {entry['event_description']}\n"
            if entry.get('insight_text'):
                formatted += f"Инсайт: {entry['insight_text']}\n"
            if entry.get('tags'):
                formatted += f"Теги: {', '.join(entry['tags'])}\n"
        
        formatted += "\n=== КОНЕЦ КОНТЕКСТА ===\n"
        
        return formatted


# Глобальный экземпляр сервиса
context_service = ContextService()
