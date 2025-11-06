"""
Сервис для работы с Redis: кеширование и очереди задач
При отсутствии Redis использует SQLite-основанную очередь (бесплатная альтернатива)
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from redis import Redis
from dotenv import load_dotenv

# Импортируем SQLite queue как fallback
try:
    from app.services.sqlite_queue_service import sqlite_queue_service
    SQLITE_QUEUE_AVAILABLE = True
except ImportError:
    SQLITE_QUEUE_AVAILABLE = False
    sqlite_queue_service = None

load_dotenv()

logger = logging.getLogger(__name__)


class RedisService:
    """Сервис для работы с Redis"""
    
    def __init__(self):
        """Инициализация Redis клиента (ленивая загрузка)"""
        # Сохраняем настройки для ленивой инициализации
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        
        # Ленивая инициализация: клиент и очередь создаются только при использовании
        self.redis_client = None
        self.context_queue = None
        self.use_sqlite_queue = None
        self._redis_initialized = False
    
    def _ensure_redis_initialized(self):
        """Обеспечивает инициализацию Redis клиента (ленивая загрузка)"""
        if self._redis_initialized:
            return
        
        try:
            self.redis_client = Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Проверка подключения
            self.redis_client.ping()
            logger.info(f"✅ Redis подключен: {self.redis_host}:{self.redis_port}")
            
            # Инициализация очереди задач
            try:
                from rq import Queue
                self.context_queue = Queue('context_tasks', connection=self.redis_client)
                logger.info("✅ Очередь задач Redis 'context_tasks' инициализирована")
                self.use_sqlite_queue = False
            except Exception as e:
                logger.warning(f"⚠️ Ошибка инициализации Redis очереди: {str(e)}")
                self.context_queue = None
                self.use_sqlite_queue = SQLITE_QUEUE_AVAILABLE
        except Exception as e:
            logger.warning(f"⚠️ Redis недоступен: {str(e)}. Очереди задач и кеш будут недоступны.")
            logger.warning("   Для запуска Redis: docker run -d -p 6379:6379 redis:latest")
            self.redis_client = None
            self.context_queue = None
            # Используем SQLite queue как fallback
            self.use_sqlite_queue = SQLITE_QUEUE_AVAILABLE
            if self.use_sqlite_queue:
                logger.info("✅ Используется SQLite-основанная очередь (бесплатная альтернатива Redis)")
        
        self._redis_initialized = True
    
    # ============ Кеширование ============
    
    def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Сохранение значения в кеш
        
        Args:
            key: Ключ кеша
            value: Значение (будет сериализовано в JSON)
            ttl: Время жизни в секундах (по умолчанию 1 час)
            
        Returns:
            True при успехе, False при ошибке
        """
        # Инициализируем Redis при необходимости (ленивая загрузка)
        self._ensure_redis_initialized()
        
        if not self.redis_client:
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            
            self.redis_client.setex(key, ttl, value_str)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кеш: {str(e)}")
            return False
    
    def cache_get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кеша
        
        Args:
            key: Ключ кеша
            
        Returns:
            Значение или None
        """
        # Инициализируем Redis при необходимости (ленивая загрузка)
        self._ensure_redis_initialized()
        
        if not self.redis_client:
            return None
        
        try:
            value_str = self.redis_client.get(key)
            if not value_str:
                return None
            
            # Пытаемся распарсить как JSON
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
        except Exception as e:
            logger.error(f"❌ Ошибка получения из кеша: {str(e)}")
            return None
    
    def cache_delete(self, key: str) -> bool:
        """
        Удаление значения из кеша
        
        Args:
            key: Ключ кеша
            
        Returns:
            True при успехе
        """
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из кеша: {str(e)}")
            return False
    
    def cache_get_pattern(self, pattern: str) -> List[str]:
        """
        Получение всех ключей по паттерну
        
        Args:
            pattern: Паттерн поиска (например, "session:*")
            
        Returns:
            Список ключей
        """
        # Инициализируем Redis при необходимости (ленивая загрузка)
        self._ensure_redis_initialized()
        
        if not self.redis_client:
            return []
        
        try:
            return list(self.redis_client.keys(pattern))
        except Exception as e:
            logger.error(f"❌ Ошибка поиска по паттерну: {str(e)}")
            return []
    
    # ============ Очереди задач ============
    
    def enqueue_task(
        self,
        task_func,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        Добавление задачи в очередь
        
        Args:
            task_func: Функция для выполнения
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            ID задачи (job_id) или None при ошибке
        """
        # Инициализируем Redis при необходимости (ленивая загрузка)
        self._ensure_redis_initialized()
        
        # Используем Redis очередь если доступна
        if self.context_queue:
            try:
                job = self.context_queue.enqueue(
                    task_func,
                    *args,
                    **kwargs,
                    job_timeout=300  # 5 минут на выполнение задачи
                )
                logger.info(f"✅ Задача добавлена в Redis очередь: {job.id}")
                return job.id
            except Exception as e:
                logger.error(f"❌ Ошибка добавления задачи в Redis очередь: {str(e)}")
                # Fallback на SQLite queue
                if self.use_sqlite_queue:
                    return self._enqueue_to_sqlite(task_func, *args, **kwargs)
                return None
        
        # Используем SQLite очередь как fallback
        if self.use_sqlite_queue:
            return self._enqueue_to_sqlite(task_func, *args, **kwargs)
        
        logger.warning("Очередь задач не инициализирована (Redis недоступен, SQLite queue недоступен)")
        return None
    
    def _enqueue_to_sqlite(self, task_func, *args, **kwargs) -> Optional[str]:
        """Добавление задачи в SQLite очередь"""
        try:
            job_timeout = kwargs.pop('job_timeout', 300)
            job_id = sqlite_queue_service.enqueue(
                task_func,
                queue_name='context_tasks',
                timeout=job_timeout,
                *args,
                **kwargs
            )
            logger.info(f"✅ Задача добавлена в SQLite очередь: {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"❌ Ошибка добавления задачи в SQLite очередь: {str(e)}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            Словарь со статусом или None
        """
        # Пытаемся получить из Redis
        if self.context_queue and self.redis_client:
            try:
                from rq.job import Job
                job = Job.fetch(job_id, connection=self.redis_client)
                if job:
                    return {
                        "id": job.id,
                        "status": job.get_status(),
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                        "result": str(job.result) if job.result else None,
                        "exc_info": job.exc_info if job.exc_info else None
                    }
            except Exception as e:
                logger.debug(f"Задача не найдена в Redis: {str(e)}")
        
        # Fallback на SQLite queue
        if self.use_sqlite_queue:
            return sqlite_queue_service.get_job_status(job_id)
        
        return None
    
    def get_queue_length(self) -> int:
        """
        Получение количества задач в очереди
        
        Returns:
            Количество задач
        """
        # Инициализируем Redis при необходимости (ленивая загрузка)
        self._ensure_redis_initialized()
        
        # Redis очередь
        if self.context_queue:
            try:
                return len(self.context_queue)
            except Exception as e:
                logger.error(f"❌ Ошибка получения длины Redis очереди: {str(e)}")
        
        # SQLite очередь
        if self.use_sqlite_queue:
            return sqlite_queue_service.get_queue_length('context_tasks')
        
        return 0
    
    # ============ Специфичные методы для контекста ============
    
    def cache_session_context(
        self,
        session_id: int,
        context_entries: List[Dict[str, Any]],
        ttl: int = 1800  # 30 минут
    ) -> bool:
        """
        Кеширование контекста сессии
        
        Args:
            session_id: ID сессии
            context_entries: Список контекстных записей
            ttl: Время жизни кеша в секундах
            
        Returns:
            True при успехе
        """
        key = f"session:context:{session_id}"
        return self.cache_set(key, context_entries, ttl)
    
    def get_cached_session_context(
        self,
        session_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Получение кешированного контекста сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список контекстных записей или None
        """
        key = f"session:context:{session_id}"
        return self.cache_get(key)
    
    def invalidate_session_context(self, session_id: int) -> bool:
        """
        Инвалидация кеша контекста сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            True при успехе
        """
        key = f"session:context:{session_id}"
        return self.cache_delete(key)


# Глобальный экземпляр сервиса
redis_service = RedisService()

