"""
SQLite-based Queue Service - бесплатная альтернатива Redis для очередей задач
Использует SQLite базу данных для хранения задач
"""
import os
import json
import uuid
import logging
import threading
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Базовый класс для моделей очереди
QueueBase = declarative_base()


class Task(QueueBase):
    """Модель задачи в очереди"""
    __tablename__ = "task_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID задачи
    queue_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(255), nullable=False)  # Имя функции для вызова
    args_json = Column(Text, nullable=True)  # Аргументы в JSON
    kwargs_json = Column(Text, nullable=True)  # Keyword arguments в JSON
    status = Column(String(20), default='queued', index=True)  # queued, started, finished, failed
    result_json = Column(Text, nullable=True)  # Результат выполнения
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    timeout = Column(Integer, default=300)  # Таймаут в секундах (5 минут по умолчанию)
    
    # Индексы для быстрого поиска
    __table_args__ = (
        Index('idx_queue_status', 'queue_name', 'status'),
        Index('idx_status_created', 'status', 'created_at'),
    )


class SQLiteQueueService:
    """Сервис очереди задач на основе SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Инициализация сервиса очереди
        
        Args:
            db_path: Путь к файлу SQLite (по умолчанию использует основную БД)
        """
        # Определяем путь к БД
        if db_path is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
            if database_url.startswith("sqlite:///"):
                # Извлекаем путь из URL
                db_path = database_url.replace("sqlite:///", "")
            else:
                # Если не SQLite, создаем отдельный файл для очереди
                db_path = "./task_queue.db"
        else:
            if not db_path.startswith("sqlite:///"):
                db_path = f"sqlite:///{db_path}"
        
        # Создаем движок для очереди
        if db_path.startswith("sqlite:///"):
            self.db_url = db_path
        else:
            self.db_url = f"sqlite:///{db_path}"
        
        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False} if self.db_url.startswith("sqlite") else {}
        )
        
        # Создаем таблицы
        QueueBase.metadata.create_all(bind=self.engine)
        
        # Сессия БД
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Lock для потокобезопасности
        self._lock = threading.Lock()
        
        logger.info(f"✅ SQLite Queue Service инициализирован: {self.db_url}")
    
    def enqueue(
        self,
        func: Callable,
        queue_name: str = 'default',
        *args,
        timeout: int = 300,
        **kwargs
    ) -> str:
        """
        Добавление задачи в очередь
        
        Args:
            func: Функция для выполнения
            queue_name: Имя очереди
            *args: Позиционные аргументы
            timeout: Таймаут выполнения в секундах
            **kwargs: Именованные аргументы
            
        Returns:
            job_id - уникальный идентификатор задачи
        """
        job_id = str(uuid.uuid4())
        
        # Сериализуем аргументы
        args_json = json.dumps(args, ensure_ascii=False, default=str) if args else None
        kwargs_json = json.dumps(kwargs, ensure_ascii=False, default=str) if kwargs else None
        
        # Имя функции (модуль.функция)
        func_name = f"{func.__module__}.{func.__name__}"
        
        with self._lock:
            db = self.SessionLocal()
            try:
                task = Task(
                    job_id=job_id,
                    queue_name=queue_name,
                    function_name=func_name,
                    args_json=args_json,
                    kwargs_json=kwargs_json,
                    status='queued',
                    timeout=timeout,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(task)
                db.commit()
                logger.info(f"✅ Задача добавлена в очередь: {job_id} ({queue_name})")
                return job_id
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка добавления задачи: {str(e)}")
                raise
            finally:
                db.close()
    
    def dequeue(self, queue_name: str = 'default', timeout: int = 60) -> Optional[Task]:
        """
        Получение следующей задачи из очереди
        
        Args:
            queue_name: Имя очереди
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Task объект или None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                db = self.SessionLocal()
                try:
                    # Ищем задачу в статусе 'queued'
                    task = db.query(Task).filter(
                        Task.queue_name == queue_name,
                        Task.status == 'queued'
                    ).order_by(Task.created_at.asc()).first()
                    
                    if task:
                        # Обновляем статус на 'started'
                        task.status = 'started'
                        task.started_at = datetime.now(timezone.utc)
                        db.commit()
                        db.refresh(task)
                        return task
                    
                    db.close()
                except Exception as e:
                    db.rollback()
                    logger.error(f"❌ Ошибка получения задачи: {str(e)}")
                    db.close()
            
            # Ждем перед следующей попыткой
            time.sleep(0.5)
        
        return None
    
    def mark_finished(self, job_id: str, result: Any = None):
        """Отметить задачу как выполненную"""
        with self._lock:
            db = self.SessionLocal()
            try:
                task = db.query(Task).filter(Task.job_id == job_id).first()
                if task:
                    task.status = 'finished'
                    task.finished_at = datetime.now(timezone.utc)
                    if result is not None:
                        task.result_json = json.dumps(result, ensure_ascii=False, default=str)
                    db.commit()
                    logger.info(f"✅ Задача выполнена: {job_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка обновления задачи: {str(e)}")
            finally:
                db.close()
    
    def mark_failed(self, job_id: str, error: str):
        """Отметить задачу как провалившуюся"""
        with self._lock:
            db = self.SessionLocal()
            try:
                task = db.query(Task).filter(Task.job_id == job_id).first()
                if task:
                    task.status = 'failed'
                    task.finished_at = datetime.now(timezone.utc)
                    task.error_message = str(error)[:1000]  # Ограничиваем длину
                    db.commit()
                    logger.error(f"❌ Задача провалена: {job_id} - {error}")
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка обновления задачи: {str(e)}")
            finally:
                db.close()
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса задачи
        
        Returns:
            Словарь со статусом или None
        """
        db = self.SessionLocal()
        try:
            task = db.query(Task).filter(Task.job_id == job_id).first()
            if not task:
                return None
            
            result = None
            if task.result_json:
                try:
                    result = json.loads(task.result_json)
                except:
                    result = task.result_json
            
            return {
                "id": task.job_id,
                "status": task.status,
                "queue_name": task.queue_name,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "finished_at": task.finished_at.isoformat() if task.finished_at else None,
                "result": result,
                "error_message": task.error_message
            }
        finally:
            db.close()
    
    def get_queue_length(self, queue_name: str = 'default') -> int:
        """Получить количество задач в очереди"""
        db = self.SessionLocal()
        try:
            return db.query(Task).filter(
                Task.queue_name == queue_name,
                Task.status == 'queued'
            ).count()
        finally:
            db.close()
    
    def cleanup_old_tasks(self, days: int = 7):
        """Удалить старые выполненные задачи"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        db = self.SessionLocal()
        try:
            deleted = db.query(Task).filter(
                Task.status.in_(['finished', 'failed']),
                Task.finished_at < cutoff_date
            ).delete()
            db.commit()
            logger.info(f"✅ Удалено {deleted} старых задач")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Ошибка очистки задач: {str(e)}")
        finally:
            db.close()


# Глобальный экземпляр сервиса
sqlite_queue_service = SQLiteQueueService()
