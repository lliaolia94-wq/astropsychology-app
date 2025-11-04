"""
Сервис кеширования для натальных карт.
Использует in-memory кеш для быстрого доступа к данным.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from threading import Lock
import time


class CacheEntry:
    """Запись в кеше"""
    def __init__(self, data: Any, timestamp: datetime, chart_calculated_at: datetime):
        self.data = data
        self.cached_at = timestamp
        self.chart_calculated_at = chart_calculated_at  # Время последнего расчета карты в БД


class NatalChartCache:
    """Кеш для натальных карт"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: Время жизни кеша в секундах (по умолчанию 1 час)
        """
        self._cache: Dict[int, CacheEntry] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds
    
    def get(self, user_id: int, chart_calculated_at: Optional[datetime] = None) -> Optional[Any]:
        """
        Получить данные из кеша.
        
        Args:
            user_id: ID пользователя
            chart_calculated_at: Время последнего расчета карты (для проверки актуальности)
            
        Returns:
            Данные из кеша или None, если кеш неактуален/отсутствует
        """
        with self._lock:
            if user_id not in self._cache:
                return None
            
            entry = self._cache[user_id]
            
            # Проверяем TTL
            age = (datetime.now(timezone.utc) - entry.cached_at).total_seconds()
            if age > self.ttl_seconds:
                del self._cache[user_id]
                return None
            
            # Если передано время расчета карты, проверяем актуальность
            if chart_calculated_at is not None:
                # Если карта была пересчитана после кеширования, кеш неактуален
                if chart_calculated_at > entry.chart_calculated_at:
                    del self._cache[user_id]
                    return None
            
            return entry.data
    
    def set(self, user_id: int, data: Any, chart_calculated_at: datetime):
        """
        Сохранить данные в кеш.
        
        Args:
            user_id: ID пользователя
            data: Данные для кеширования
            chart_calculated_at: Время расчета карты
        """
        with self._lock:
            self._cache[user_id] = CacheEntry(
                data=data,
                timestamp=datetime.now(timezone.utc),
                chart_calculated_at=chart_calculated_at
            )
    
    def invalidate(self, user_id: int):
        """
        Инвалидировать кеш для пользователя.
        
        Args:
            user_id: ID пользователя
        """
        with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
    
    def clear(self):
        """Очистить весь кеш"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Получить количество записей в кеше"""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self):
        """Удалить устаревшие записи из кеша"""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired_keys = [
                user_id for user_id, entry in self._cache.items()
                if (now - entry.cached_at).total_seconds() > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Глобальный экземпляр кеша
# TTL = 1 час (3600 секунд)
natal_chart_cache = NatalChartCache(ttl_seconds=3600)

