"""
Унифицированный сервисный слой для работы с данными контекста

Предоставляет единый интерфейс для всех модулей отбора контекста,
включая кэширование, пагинацию и оптимизацию запросов.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.database.models import ContextEntry
from app.services.context_selection.config import ContextSelectionConfig

logger = logging.getLogger(__name__)


class ContextDataService:
    """
    Унифицированный сервис для работы с данными контекста
    
    Предоставляет оптимизированные методы для получения данных
    с автоматическим кэшированием и пагинацией.
    """
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
        # TODO: Добавить поддержку module_caches таблицы когда она будет создана
        self._cache_enabled = True
    
    def get_entries_for_period(
        self,
        db: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
        order_by: str = 'created_at'
    ) -> List[ContextEntry]:
        """
        Получение событий за период с кэшированием и пагинацией
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            limit: Максимальное количество записей (None = без ограничений)
            order_by: Поле для сортировки ('created_at' или 'priority')
            
        Returns:
            Список событий за указанный период
        """
        try:
            # Проверяем кэш (если включен)
            cache_key = f"entries_period_{user_id}_{start_date.date()}_{end_date.date()}"
            if self._cache_enabled:
                # TODO: Реализовать проверку кэша из module_caches
                pass
            
            # Формируем запрос
            query = db.query(ContextEntry).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.created_at >= start_date,
                    ContextEntry.created_at <= end_date
                )
            )
            
            # Сортировка
            if order_by == 'created_at':
                query = query.order_by(desc(ContextEntry.created_at))
            elif order_by == 'priority':
                query = query.order_by(desc(ContextEntry.priority), desc(ContextEntry.created_at))
            
            # Пагинация
            if limit:
                query = query.limit(limit)
            
            entries = query.all()
            
            # Сохраняем в кэш (если включен)
            if self._cache_enabled and entries:
                # TODO: Реализовать сохранение в module_caches
                pass
            
            logger.debug(f"Получено {len(entries)} событий для пользователя {user_id} за период")
            return entries
            
        except Exception as e:
            logger.error(f"Ошибка получения событий за период: {str(e)}", exc_info=True)
            return []
    
    def get_emotional_entries(
        self,
        db: Session,
        user_id: int,
        emotion: str,
        limit: int = 50,
        start_date: Optional[datetime] = None
    ) -> List[ContextEntry]:
        """
        Получение событий по эмоциональному состоянию
        
        Использует предварительно рассчитанные индексы для быстрого поиска.
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            emotion: Эмоциональное состояние
            limit: Максимальное количество записей
            start_date: Начальная дата для фильтрации (опционально)
            
        Returns:
            Список событий с указанным эмоциональным состоянием
        """
        try:
            query = db.query(ContextEntry).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.emotional_state == emotion
                )
            )
            
            if start_date:
                query = query.filter(ContextEntry.created_at >= start_date)
            
            query = query.order_by(desc(ContextEntry.created_at)).limit(limit)
            
            entries = query.all()
            logger.debug(f"Получено {len(entries)} событий с эмоцией '{emotion}' для пользователя {user_id}")
            return entries
            
        except Exception as e:
            logger.error(f"Ошибка получения событий по эмоции: {str(e)}", exc_info=True)
            return []
    
    def get_entries_by_category(
        self,
        db: Session,
        user_id: int,
        category: str,
        limit: int = 50,
        start_date: Optional[datetime] = None
    ) -> List[ContextEntry]:
        """
        Получение событий по категории
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            category: Категория события
            limit: Максимальное количество записей
            start_date: Начальная дата для фильтрации (опционально)
            
        Returns:
            Список событий указанной категории
        """
        try:
            query = db.query(ContextEntry).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.category == category
                )
            )
            
            if start_date:
                query = query.filter(ContextEntry.created_at >= start_date)
            
            query = query.order_by(desc(ContextEntry.created_at)).limit(limit)
            
            entries = query.all()
            logger.debug(f"Получено {len(entries)} событий категории '{category}' для пользователя {user_id}")
            return entries
            
        except Exception as e:
            logger.error(f"Ошибка получения событий по категории: {str(e)}", exc_info=True)
            return []
    
    def get_entries_by_tags(
        self,
        db: Session,
        user_id: int,
        tags: List[str],
        limit: int = 50,
        match_all: bool = False
    ) -> List[ContextEntry]:
        """
        Получение событий по тегам
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            tags: Список тегов для поиска
            limit: Максимальное количество записей
            match_all: Если True, событие должно содержать все теги; если False - любой тег
            
        Returns:
            Список событий, содержащих указанные теги
        """
        try:
            if not tags:
                return []
            
            query = db.query(ContextEntry).filter(
                ContextEntry.user_id == user_id
            )
            
            # Поиск по тегам (зависит от типа данных в БД)
            # Если tags - это массив, используем специальные операторы
            if match_all:
                # Все теги должны присутствовать
                for tag in tags:
                    query = query.filter(ContextEntry.tags.contains([tag]))
            else:
                # Любой тег должен присутствовать
                from sqlalchemy import or_
                conditions = [ContextEntry.tags.contains([tag]) for tag in tags]
                query = query.filter(or_(*conditions))
            
            query = query.order_by(desc(ContextEntry.created_at)).limit(limit)
            
            entries = query.all()
            logger.debug(f"Получено {len(entries)} событий с тегами {tags} для пользователя {user_id}")
            return entries
            
        except Exception as e:
            logger.error(f"Ошибка получения событий по тегам: {str(e)}", exc_info=True)
            return []
    
    def get_entries_count(
        self,
        db: Session,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Получение количества событий пользователя
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            Количество событий
        """
        try:
            query = db.query(func.count(ContextEntry.id)).filter(
                ContextEntry.user_id == user_id
            )
            
            if start_date:
                query = query.filter(ContextEntry.created_at >= start_date)
            if end_date:
                query = query.filter(ContextEntry.created_at <= end_date)
            
            count = query.scalar() or 0
            return count
            
        except Exception as e:
            logger.error(f"Ошибка подсчета событий: {str(e)}", exc_info=True)
            return 0
    
    def update_module_cache(
        self,
        db: Session,
        user_id: int,
        module: str,
        key: str,
        data: dict,
        ttl_hours: int = 24
    ):
        """
        Обновление кэша модуля
        
        TODO: Реализовать после создания таблицы module_caches
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            module: Название модуля ('freshness', 'emotions', 'patterns', 'karma')
            key: Ключ кэша
            data: Данные для кэширования
            ttl_hours: Время жизни кэша в часах
        """
        # TODO: Реализовать сохранение в таблицу module_caches
        # expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        # cache_entry = ModuleCache(
        #     user_id=user_id,
        #     module_name=module,
        #     cache_key=key,
        #     cache_data=data,
        #     expires_at=expires_at
        # )
        # db.add(cache_entry)
        # db.commit()
        pass
    
    def get_module_cache(
        self,
        db: Session,
        user_id: int,
        module: str,
        key: str
    ) -> Optional[dict]:
        """
        Получение данных из кэша модуля
        
        TODO: Реализовать после создания таблицы module_caches
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            module: Название модуля
            key: Ключ кэша
            
        Returns:
            Данные из кэша или None, если кэш отсутствует/устарел
        """
        # TODO: Реализовать получение из таблицы module_caches
        # cache_entry = db.query(ModuleCache).filter(
        #     and_(
        #         ModuleCache.user_id == user_id,
        #         ModuleCache.module_name == module,
        #         ModuleCache.cache_key == key,
        #         ModuleCache.expires_at > datetime.now(timezone.utc)
        #     )
        # ).first()
        # 
        # if cache_entry:
        #     return cache_entry.cache_data
        # return None
        return None
    
    def clear_module_cache(
        self,
        db: Session,
        user_id: Optional[int] = None,
        module: Optional[str] = None
    ):
        """
        Очистка кэша модуля
        
        TODO: Реализовать после создания таблицы module_caches
        
        Args:
            db: Сессия БД
            user_id: ID пользователя (опционально, если None - очистить для всех)
            module: Название модуля (опционально, если None - очистить для всех)
        """
        # TODO: Реализовать очистку кэша
        # query = db.query(ModuleCache).filter(
        #     ModuleCache.expires_at < datetime.now(timezone.utc)
        # )
        # if user_id:
        #     query = query.filter(ModuleCache.user_id == user_id)
        # if module:
        #     query = query.filter(ModuleCache.module_name == module)
        # query.delete()
        # db.commit()
        pass


# Глобальный экземпляр сервиса
context_data_service = ContextDataService()

