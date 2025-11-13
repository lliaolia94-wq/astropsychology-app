"""
Класс для параметризованных запросов к регистрам контекстной информации
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class ContextSlice:
    """Результат выполнения запроса - виртуальный срез данных"""
    events: List[Dict[str, Any]] = field(default_factory=list)
    contacts: List[Dict[str, Any]] = field(default_factory=list)
    transits: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    patterns: List[Dict[str, Any]] = field(default_factory=list)


class ContextQuery:
    """
    Класс для построения параметризованных запросов к регистрам
    
    Пример использования:
        query = (ContextQuery(user_id=123)
            .for_period(start_date=month_ago, end_date=now)
            .with_categories(['career', 'relationships'])
            .with_emotional_state(['anxiety', 'frustration'])
            .include_transits()
            .execute())
    """
    
    def __init__(self, user_id: int, db=None):
        """
        Инициализация запроса
        
        Args:
            user_id: ID пользователя
            db: Сессия базы данных (опционально, можно передать при execute)
        """
        self.user_id = user_id
        self.db = db
        self.filters: Dict[str, Any] = {}
        self.time_range: Dict[str, Optional[datetime]] = {}
        self.categories: List[str] = []
        self.emotional_states: List[str] = []
        self.tags: List[str] = []
        self.include_contacts = False
        self.include_transits = False
        self.include_karmic_themes = False
        self.priority_min: Optional[int] = None
        self.priority_max: Optional[int] = None
        self.limit: Optional[int] = None
    
    def for_period(self, start_date: datetime, end_date: datetime) -> 'ContextQuery':
        """
        Установка временного диапазона
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            self для цепочки вызовов
        """
        self.time_range = {'start': start_date, 'end': end_date}
        return self
    
    def for_days(self, days: int, end_date: Optional[datetime] = None) -> 'ContextQuery':
        """
        Установка периода в днях от текущей даты или указанной даты
        
        Args:
            days: Количество дней назад
            end_date: Конечная дата (по умолчанию сейчас)
            
        Returns:
            self для цепочки вызовов
        """
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.for_period(start_date, end_date)
    
    def with_categories(self, categories: List[str]) -> 'ContextQuery':
        """
        Фильтрация по категориям
        
        Args:
            categories: Список категорий (career, health, relationships, finance, spiritual)
            
        Returns:
            self для цепочки вызовов
        """
        self.categories = categories
        return self
    
    def with_emotional_state(self, emotions: List[str]) -> 'ContextQuery':
        """
        Фильтрация по эмоциональным состояниям
        
        Args:
            emotions: Список эмоциональных состояний
            
        Returns:
            self для цепочки вызовов
        """
        self.emotional_states = emotions
        return self
    
    def with_tags(self, tags: List[str]) -> 'ContextQuery':
        """
        Фильтрация по тегам
        
        Args:
            tags: Список тегов
            
        Returns:
            self для цепочки вызовов
        """
        self.tags = tags
        return self
    
    def with_priority(self, min_priority: Optional[int] = None, max_priority: Optional[int] = None) -> 'ContextQuery':
        """
        Фильтрация по приоритету
        
        Args:
            min_priority: Минимальный приоритет (1-5)
            max_priority: Максимальный приоритет (1-5)
            
        Returns:
            self для цепочки вызовов
        """
        self.priority_min = min_priority
        self.priority_max = max_priority
        return self
    
    def include_contacts(self) -> 'ContextQuery':
        """
        Включить контакты в результат
        
        Returns:
            self для цепочки вызовов
        """
        self.include_contacts = True
        return self
    
    def include_transits(self) -> 'ContextQuery':
        """
        Включить транзиты в результат
        
        Returns:
            self для цепочки вызовов
        """
        self.include_transits = True
        return self
    
    def include_karmic_themes(self) -> 'ContextQuery':
        """
        Включить кармические темы в результат
        
        Returns:
            self для цепочки вызовов
        """
        self.include_karmic_themes = True
        return self
    
    def set_limit(self, limit: int) -> 'ContextQuery':
        """
        Установка лимита результатов
        
        Args:
            limit: Максимальное количество результатов
            
        Returns:
            self для цепочки вызовов
        """
        self.limit = limit
        return self
    
    def execute(self, db=None) -> ContextSlice:
        """
        Выполняет запрос и возвращает виртуальный срез
        
        Args:
            db: Сессия базы данных (если не передана при инициализации)
            
        Returns:
            ContextSlice с результатами запроса
        """
        from app.services.registers_service import registers_service
        
        if db is None:
            db = self.db
        
        if db is None:
            raise ValueError("Необходимо передать сессию БД либо при инициализации, либо при execute()")
        
        return registers_service.execute_query(self, db)

