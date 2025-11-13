"""
Вспомогательные утилиты для модулей интеллектуального отбора контекста
"""
import logging
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Callable, TypeVar, Tuple
from datetime import datetime, timedelta, timezone
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def timing_decorator(func: Callable) -> Callable:
    """Декоратор для измерения времени выполнения функции"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        logger.debug(f"{func.__name__} выполнена за {processing_time_ms:.2f} мс")
        return result, processing_time_ms
    return wrapper


def calculate_time_weight(
    event_date: datetime,
    current_date: datetime,
    period_days: int = 30,
    decay_factor: float = 0.1
) -> float:
    """
    Расчет веса события с учетом временного фактора
    
    Args:
        event_date: Дата события
        current_date: Текущая дата
        period_days: Период охвата в днях
        decay_factor: Коэффициент убывания значимости
        
    Returns:
        Вес события (0.0 - 1.0)
    """
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    if current_date.tzinfo is None:
        current_date = current_date.replace(tzinfo=timezone.utc)
    
    time_diff = (current_date - event_date).total_seconds() / 86400  # дни
    
    if time_diff < 0:
        return 1.0  # Будущие события (не должны быть)
    
    if time_diff > period_days:
        return 0.0  # События за пределами периода
    
    # Экспоненциальное убывание значимости
    weight = 1.0 / (1.0 + decay_factor * time_diff)
    
    return max(0.0, min(1.0, weight))


def normalize_score(score: float, min_score: float = 0.0, max_score: float = 1.0) -> float:
    """Нормализация оценки в диапазон [0.0, 1.0]"""
    if max_score == min_score:
        return 0.0
    normalized = (score - min_score) / (max_score - min_score)
    return max(0.0, min(1.0, normalized))


def combine_scores(scores: List[float], weights: Optional[List[float]] = None) -> float:
    """
    Комбинирование нескольких оценок с весами
    
    Args:
        scores: Список оценок
        weights: Список весов (если None, используются равные веса)
        
    Returns:
        Комбинированная оценка
    """
    if not scores:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(scores)
    
    if len(scores) != len(weights):
        weights = [1.0] * len(scores)
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    return weighted_sum / total_weight


def filter_by_date_range(
    events: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    date_field: str = "created_at"
) -> List[Dict[str, Any]]:
    """
    Фильтрация событий по диапазону дат
    
    Args:
        events: Список событий
        start_date: Начальная дата
        end_date: Конечная дата
        date_field: Поле с датой
        
    Returns:
        Отфильтрованный список событий
    """
    filtered = []
    for event in events:
        event_date = event.get(date_field)
        if not event_date:
            continue
        
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except ValueError:
                continue
        
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        if start_date <= event_date <= end_date:
            filtered.append(event)
    
    return filtered


def remove_duplicates(
    events: List[Dict[str, Any]],
    key_field: str = "id"
) -> List[Dict[str, Any]]:
    """
    Удаление дубликатов событий
    
    Args:
        events: Список событий
        key_field: Поле для идентификации дубликатов
        
    Returns:
        Список уникальных событий
    """
    seen = set()
    unique_events = []
    
    for event in events:
        key = event.get(key_field)
        if key is None:
            continue
        
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    return unique_events


def estimate_tokens(text: str) -> int:
    """
    Оценка количества токенов в тексте (приблизительная)
    
    Args:
        text: Текст
        
    Returns:
        Приблизительное количество токенов
    """
    # Простая оценка: ~4 символа на токен для русского языка
    return len(text) // 4


def truncate_text(text: str, max_tokens: int) -> str:
    """
    Обрезка текста до указанного количества токенов
    
    Args:
        text: Текст
        max_tokens: Максимальное количество токенов
        
    Returns:
        Обрезанный текст
    """
    estimated_tokens = estimate_tokens(text)
    if estimated_tokens <= max_tokens:
        return text
    
    max_chars = max_tokens * 4
    return text[:max_chars] + "..."


def safe_execute(
    func: Callable[[], T],
    fallback: T,
    error_message: str,
    log_error: bool = True
) -> T:
    """
    Безопасное выполнение функции с обработкой ошибок
    
    Args:
        func: Функция для выполнения
        fallback: Значение по умолчанию при ошибке
        error_message: Сообщение об ошибке
        log_error: Логировать ли ошибку
        
    Returns:
        Результат функции или fallback при ошибке
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"{error_message}: {str(e)}", exc_info=True)
        return fallback


def generate_cache_key(prefix: str, **kwargs) -> str:
    """
    Генерация ключа кэша на основе параметров
    
    Args:
        prefix: Префикс ключа
        **kwargs: Параметры для ключа
        
    Returns:
        Хеш-ключ для кэша
    """
    # Сортируем параметры для консистентности
    sorted_params = json.dumps(kwargs, sort_keys=True, default=str)
    param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:16]
    return f"context_selection:{prefix}:{param_hash}"


def batch_query(
    db,
    model_class,
    filter_conditions: List[Any],
    batch_size: int = 100
) -> List[Any]:
    """
    Пакетный запрос к БД для избежания N+1 проблем
    
    Args:
        db: Сессия БД
        model_class: Класс модели
        filter_conditions: Список условий фильтрации
        batch_size: Размер батча
        
    Returns:
        Список результатов
    """
    if not filter_conditions:
        return []
    
    try:
        # Используем IN для пакетного запроса
        results = db.query(model_class).filter(
            model_class.id.in_(filter_conditions)
        ).all()
        return results
    except Exception as e:
        logger.error(f"Ошибка пакетного запроса: {str(e)}", exc_info=True)
        return []


def determine_event_category(entry) -> 'EventCategory':
    """
    Универсальная функция определения категории события
    
    Используется во всех модулях для избежания дублирования логики.
    
    Args:
        entry: Объект ContextEntry
        
    Returns:
        EventCategory - категория события
    """
    from app.services.context_selection.models import EventCategory
    
    tags = entry.tags if entry.tags else []
    tags_lower = [tag.lower() for tag in tags]
    
    # Проверяем теги для определения категории
    if any(tag in tags_lower for tag in ['конфликт', 'конфликтный', 'conflict']):
        return EventCategory.CONFLICT
    elif any(tag in tags_lower for tag in ['решение', 'выбор', 'decision']):
        return EventCategory.DECISION
    elif any(tag in tags_lower for tag in ['достижение', 'успех', 'achievement']):
        return EventCategory.ACHIEVEMENT
    elif any(tag in tags_lower for tag in ['отношения', 'relationship']):
        return EventCategory.RELATIONSHIP
    elif any(tag in tags_lower for tag in ['здоровье', 'health']):
        return EventCategory.HEALTH
    elif any(tag in tags_lower for tag in ['финансы', 'finance']):
        return EventCategory.FINANCE
    elif any(tag in tags_lower for tag in ['духовность', 'spiritual']):
        return EventCategory.SPIRITUAL
    elif any(tag in tags_lower for tag in ['астрология', 'astrology']):
        return EventCategory.ASTROLOGY
    else:
        return EventCategory.GENERAL


def format_event_text(entry, max_length: int = 200) -> str:
    """
    Универсальная функция форматирования текста события
    
    Используется во всех модулях для избежания дублирования логики.
    
    Args:
        entry: Объект ContextEntry
        max_length: Максимальная длина текста (по умолчанию 200 символов)
        
    Returns:
        Отформатированный текст события
    """
    parts = []
    
    # Приоритет: event_description > user_message > ai_response
    if entry.event_description:
        text = entry.event_description
        if len(text) > max_length:
            text = text[:max_length] + "..."
        parts.append(text)
    elif entry.user_message:
        text = entry.user_message
        if len(text) > max_length:
            text = text[:max_length] + "..."
        parts.append(text)
    
    # Добавляем инсайт, если есть
    if entry.insight_text:
        insight_text = entry.insight_text
        if len(insight_text) > 150:
            insight_text = insight_text[:150] + "..."
        parts.append(f"Инсайт: {insight_text}")
    
    # Если нет основных полей, используем комбинацию
    if not parts:
        if entry.user_message:
            text = entry.user_message[:max_length]
            parts.append(text)
        if entry.ai_response:
            text = entry.ai_response[:max_length]
            parts.append(text)
    
    result = " | ".join(parts) if parts else "Событие без описания"
    
    # Ограничиваем общую длину
    if len(result) > max_length * 2:
        result = result[:max_length * 2] + "..."
    
    return result

