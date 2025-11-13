"""
МОДУЛЬ 1: ПРИОРИТЕТ СВЕЖЕСТИ

Назначение: Отбор наиболее актуальных событий с учетом временнóго фактора.

Алгоритм работы:
1. Фильтрация по дате: отбор событий за указанный период
2. Временное взвешивание: расчет веса каждого события по формуле убывающей значимости
3. Ранжирование: сортировка событий по комбинированному весу (время + релевантность)
4. Лимитирование: выбор топ-N событий для включения в контекст

ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ:
- Используется пагинация для ограничения количества обрабатываемых записей
- Веса для комбинирования оценок настраиваются через конфигурацию
- Определение категории вынесено в общую утилиту (избежание дублирования)

РЕКОМЕНДАЦИЯ ПО ОПТИМИЗАЦИИ БД:
Для больших объемов данных рекомендуется создать оптимизированную таблицу:
CREATE TABLE context_entries_freshness (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    time_weight DECIMAL(3,2) NOT NULL,
    priority_weight DECIMAL(3,2) NOT NULL,
    combined_score DECIMAL(3,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    emotional_state VARCHAR(50),
    last_accessed TIMESTAMP,
    INDEX idx_user_freshness (user_id, combined_score DESC),
    INDEX idx_user_category (user_id, category, combined_score DESC)
);
Это позволит кэшировать расчеты и ускорить запросы.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.database.models import ContextEntry
from app.services.context_selection.models import (
    SelectedEvent, FreshnessResult, EventCategory, EmotionalState
)
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.utils import (
    calculate_time_weight, combine_scores, filter_by_date_range,
    remove_duplicates, timing_decorator, safe_execute, determine_event_category,
    format_event_text
)

logger = logging.getLogger(__name__)


class FreshnessModule:
    """Модуль приоритета свежести событий"""
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
    
    def select_relevant_events(
        self,
        db: Session,
        user_id: int,
        current_date: Optional[datetime] = None,
        period_days: Optional[int] = None,
        limit: Optional[int] = None,
        current_query: Optional[str] = None,
        similarity_scores: Optional[Dict[int, float]] = None
    ) -> FreshnessResult:
        """
        Отбор наиболее релевантных недавних событий
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            current_date: Текущая дата (по умолчанию - сейчас)
            period_days: Период охвата в днях (по умолчанию из конфига)
            limit: Лимит событий (по умолчанию из конфига)
            current_query: Текущий запрос пользователя (для семантического поиска)
            similarity_scores: Словарь {entry_id: similarity_score} для учета релевантности
            
        Returns:
            FreshnessResult с отобранными событиями
        """
        start_time = datetime.now()
        
        if current_date is None:
            current_date = datetime.now(timezone.utc)
        if period_days is None:
            period_days = self.config.FRESHNESS_DEFAULT_PERIOD_DAYS
        if limit is None:
            limit = self.config.FRESHNESS_DEFAULT_LIMIT
        
        # 1. Фильтрация по дате: отбор событий за указанный период
        start_date = current_date - timedelta(days=period_days)
        
        # Получаем события пользователя за период с пагинацией
        # Ограничиваем количество записей для обработки, чтобы избежать загрузки миллионов записей
        max_processing_limit = self.config.FRESHNESS_MAX_PROCESSING_LIMIT
        
        try:
            # Сначала получаем общее количество для статистики
            total_count_query = db.query(func.count(ContextEntry.id)).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.created_at >= start_date,
                    ContextEntry.created_at <= current_date
                )
            )
            total_processed = total_count_query.scalar() or 0
            
            # Получаем ограниченное количество записей для обработки
            # Используем больший лимит, чтобы учесть фильтрацию после взвешивания
            processing_limit = min(max_processing_limit, total_processed)
            
            query = db.query(ContextEntry).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.created_at >= start_date,
                    ContextEntry.created_at <= current_date
                )
            ).order_by(desc(ContextEntry.created_at)).limit(processing_limit)
            
            entries = query.all()
            
            if total_processed > processing_limit:
                logger.warning(
                    f"Обрабатывается {processing_limit} из {total_processed} событий. "
                    f"Увеличьте FRESHNESS_MAX_PROCESSING_LIMIT для обработки всех событий."
                )
                # ПРИМЕЧАНИЕ: Убедитесь, что лимит достаточно высокий для получения
                # релевантных результатов. Рекомендуется минимум 1000-2000 записей
                # для периода в 30 дней при активном использовании.
        except Exception as e:
            logger.error(f"Ошибка запроса к БД в модуле свежести: {str(e)}", exc_info=True)
            return FreshnessResult(
                events=[],
                total_processed=0,
                period_days=period_days,
                processing_time_ms=0.0
            )
        
        logger.info(f"Найдено {total_processed} событий за период {period_days} дней")
        
        # 2. Временное взвешивание и ранжирование
        scored_events = []
        
        for entry in entries:
            try:
                # Рассчитываем временной вес
                time_weight = calculate_time_weight(
                    event_date=entry.created_at,
                    current_date=current_date,
                    period_days=period_days,
                    decay_factor=self.config.FRESHNESS_DECAY_FACTOR
                )
                
                # Учитываем приоритет события
                priority_weight = entry.priority / 5.0 if entry.priority else 0.5
                
                # Учитываем семантическую релевантность (если есть)
                similarity_weight = 1.0
                if similarity_scores and entry.id in similarity_scores:
                    similarity_weight = similarity_scores[entry.id]
                
                # Комбинированный вес (веса из конфигурации)
                combined_weight = combine_scores(
                    scores=[time_weight, priority_weight, similarity_weight],
                    weights=[
                        self.config.FRESHNESS_TIME_WEIGHT,
                        self.config.FRESHNESS_PRIORITY_WEIGHT,
                        self.config.FRESHNESS_SIMILARITY_WEIGHT
                    ]
                )
                
                # Определяем категорию события (используем общую утилиту)
                category = determine_event_category(entry)
                
                # Определяем эмоциональное состояние
                emotional_state = None
                if entry.emotional_state:
                    try:
                        emotional_state = EmotionalState(entry.emotional_state.lower())
                    except ValueError:
                        pass
                
                # Формируем текст события (используем общую утилиту)
                event_text = format_event_text(entry)
                
                scored_events.append({
                    'entry': entry,
                    'weight': combined_weight,
                    'time_weight': time_weight,
                    'priority_weight': priority_weight,
                    'similarity_weight': similarity_weight,
                    'category': category,
                    'emotional_state': emotional_state,
                    'text': event_text
                })
            except Exception as e:
                logger.error(f"Ошибка обработки события {entry.id} в модуле свежести: {str(e)}", exc_info=True)
                continue
        
        # 3. Сортировка по комбинированному весу
        scored_events.sort(key=lambda x: x['weight'], reverse=True)
        
        # 4. Лимитирование: выбор топ-N событий
        selected_entries = scored_events[:limit]
        
        # Преобразуем в SelectedEvent
        selected_events = []
        for item in selected_entries:
            entry = item['entry']
            event = SelectedEvent(
                id=entry.id,
                text=item['text'],
                date=entry.created_at,
                significance_score=item['weight'],
                category=item['category'],
                emotional_state=item['emotional_state'],
                tags=entry.tags if entry.tags else [],
                similarity_score=item['similarity_weight'] if item['similarity_weight'] < 1.0 else None,
                source='freshness_module'
            )
            selected_events.append(event)
        
        # Вычисляем время обработки
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Отобрано {len(selected_events)} событий за {processing_time_ms:.2f} мс")
        
        return FreshnessResult(
            events=selected_events,
            total_processed=total_processed,
            period_days=period_days,
            processing_time_ms=processing_time_ms
        )
    

