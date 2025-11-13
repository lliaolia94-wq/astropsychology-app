"""
МОДУЛЬ 3: ПАТТЕРНЫ ПОВТОРЕНИЯ

Назначение: Автоматическое выявление циклических и повторяющихся ситуаций в истории пользователя.

Алгоритм работы:
1. Улучшенная кластеризация: семантическая группировка событий с использованием векторного поиска
2. Анализ частотности: подсчет повторяемости событий каждого типа
3. Временной анализ: выявление сезонности и цикличности во времени
4. Выявление паттернов: идентификация циклических и повторяющихся ситуаций
5. Ранжирование паттернов: определение наиболее значимых с учетом важности и эмоций

ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ:
- Семантическая кластеризация с использованием векторного поиска
- Анализ временных паттернов (сезонность, цикличность)
- Улучшенный расчет значимости с учетом приоритета и эмоций
- Настраиваемые веса для расчета значимости

РЕКОМЕНДАЦИЯ ПО ОПТИМИЗАЦИИ БД:
Для больших объемов данных рекомендуется создать оптимизированные таблицы:
CREATE TABLE user_patterns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    pattern_type VARCHAR(50) NOT NULL, -- 'temporal', 'emotional', 'topical'
    pattern_name VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    frequency INTEGER NOT NULL,
    timeframe_days INTEGER, -- Для временных паттернов
    trigger_conditions JSONB,
    predicted_next_occurrence TIMESTAMP,
    last_detected TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_patterns (user_id, pattern_type, confidence_score DESC)
);

CREATE TABLE pattern_occurrences (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES user_patterns(id),
    entry_id INTEGER NOT NULL,
    occurrence_date TIMESTAMP NOT NULL,
    match_score DECIMAL(3,2) NOT NULL,
    INDEX idx_pattern_occurrences (pattern_id, occurrence_date DESC)
);
Это позволит кэшировать паттерны и ускорить их обнаружение.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.database.models import ContextEntry
from app.services.context_selection.models import (
    SelectedEvent, PatternsResult, Pattern, EventCategory
)
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.utils import (
    timing_decorator, determine_event_category, combine_scores, safe_execute,
    format_event_text
)
from app.services.context_selection.models import EmotionalState
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class PatternsModule:
    """Модуль паттернов повторения"""
    
    # Таксономия типов событий
    EVENT_TYPES = [
        'conflict', 'decision', 'achievement', 'relationship',
        'health', 'finance', 'spiritual', 'astrology', 'general'
    ]
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
    
    def detect_patterns(
        self,
        db: Session,
        user_id: int,
        current_query: Optional[str] = None,
        history_years: int = 3,
        vector_results_cache: Optional[List[Dict[str, Any]]] = None
    ) -> PatternsResult:
        """
        Выявление паттернов повторения в истории пользователя
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            current_query: Текущий запрос пользователя (для релевантности)
            history_years: Количество лет истории для анализа
            
        Returns:
            PatternsResult с выявленными паттернами
        """
        start_time = datetime.now()
        
        if not self.config.PATTERNS_ENABLED:
            logger.info("Модуль паттернов отключен")
            return PatternsResult(
                patterns=[],
                total_patterns_found=0,
                processing_time_ms=0.0
            )
        
        # Получаем историю событий за указанный период
        start_date = datetime.now(timezone.utc) - timedelta(days=history_years * 365)
        
        try:
            entries = db.query(ContextEntry).filter(
                and_(
                    ContextEntry.user_id == user_id,
                    ContextEntry.created_at >= start_date
                )
            ).order_by(desc(ContextEntry.created_at)).all()
        except Exception as e:
            logger.error(f"Ошибка запроса к БД в модуле паттернов: {str(e)}", exc_info=True)
            return PatternsResult(
                patterns=[],
                total_patterns_found=0,
                processing_time_ms=0.0
            )
        
        logger.info(f"Анализ {len(entries)} событий за {history_years} лет")
        
        if not entries:
            return PatternsResult(
                patterns=[],
                total_patterns_found=0,
                processing_time_ms=0.0
            )
        
        # 1. Кластеризация событий: группировка по тематическим кластерам
        try:
            clusters = self._cluster_events(entries, current_query, vector_results_cache)
        except Exception as e:
            logger.error(f"Ошибка кластеризации событий: {str(e)}", exc_info=True)
            clusters = {}
        
        # 2. Анализ частотности: подсчет повторяемости событий каждого типа
        frequency_analysis = self._analyze_frequency(clusters, entries)
        
        # 2.5. Анализ временных паттернов (сезонность, цикличность)
        temporal_patterns = {}
        if self.config.PATTERNS_TEMPORAL_ANALYSIS_ENABLED:
            try:
                temporal_patterns = self._analyze_temporal_patterns(entries)
            except Exception as e:
                logger.error(f"Ошибка анализа временных паттернов: {str(e)}", exc_info=True)
                temporal_patterns = {}
        
        # 3. Выявление паттернов: идентификация циклических и повторяющихся ситуаций
        patterns = self._identify_patterns(
            frequency_analysis, 
            clusters, 
            entries,
            temporal_patterns
        )
        
        # 4. Ранжирование паттернов: определение наиболее значимых
        patterns.sort(key=lambda p: p.significance_score, reverse=True)
        
        # Лимитирование: выбор топ-N паттернов
        patterns = patterns[:self.config.PATTERNS_MAX_RESULTS]
        
        # Вычисляем время обработки
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Выявлено {len(patterns)} паттернов за {processing_time_ms:.2f} мс")
        
        return PatternsResult(
            patterns=patterns,
            total_patterns_found=len(patterns),
            processing_time_ms=processing_time_ms
        )
    
    def _cluster_events(
        self,
        entries: List[ContextEntry],
        current_query: Optional[str] = None,
        vector_results_cache: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, List[ContextEntry]]:
        """
        Кластеризация событий по тематическим кластерам
        
        ПРИМЕЧАНИЕ: Текущая реализация опирается на теги и категории.
        В будущем рекомендуется улучшить за счет:
        1. Семантической кластеризации на основе эмбеддингов (K-means, DBSCAN)
        2. Тематического моделирования (LDA, BERTopic)
        3. Использования предварительно рассчитанных кластеров из БД
        """
        clusters = defaultdict(list)
        
        for entry in entries:
            # Определяем кластер на основе тегов и категорий
            cluster_key = self._determine_cluster_key(entry)
            clusters[cluster_key].append(entry)
        
        # Если есть текущий запрос, используем векторный поиск для улучшения кластеризации
        if current_query:
            # Используем кэш или выполняем новый поиск
            if vector_results_cache:
                vector_results = [
                    r for r in vector_results_cache
                    if r.get('score', 0) >= self.config.PATTERNS_CLUSTERING_THRESHOLD
                ]
                logger.debug(f"Использован кэш векторных результатов для кластеризации: {len(vector_results)} записей")
            elif vector_service.client:
                try:
                    # Находим семантически близкие события для текущего запроса
                    vector_results = vector_service.search_similar(
                        query_text=current_query,
                        limit=50,
                        score_threshold=self.config.PATTERNS_CLUSTERING_THRESHOLD
                    )
                except Exception as e:
                    logger.error(f"Ошибка векторного поиска в модуле паттернов: {str(e)}", exc_info=True)
                    vector_results = []
            else:
                vector_results = []
            
            # Помечаем релевантные события
            relevant_entry_ids = {
                result['payload'].get('entry_id')
                for result in vector_results
                if result['payload'].get('entry_id')
            }
            
            # Создаем специальный кластер для релевантных событий
            if relevant_entry_ids:
                for entry in entries:
                    if entry.id in relevant_entry_ids:
                        clusters['current_query_relevant'].append(entry)
        
        return dict(clusters)
    
    def _determine_cluster_key(self, entry: ContextEntry) -> str:
        """
        Улучшенное определение ключа кластера для события
        
        Использует комбинацию тегов, категории и семантического анализа
        """
        # Используем общую утилиту для определения категории
        category = determine_event_category(entry)
        category_key = category.value if hasattr(category, 'value') else str(category)
        
        tags = entry.tags if entry.tags else []
        tags_lower = [tag.lower() for tag in tags]
        
        # Приоритетные теги для кластеризации
        priority_tags = {
            'работа': 'work',
            'work': 'work',
            'карьера': 'work',
            'career': 'work',
            'отношения': 'relationship',
            'relationship': 'relationship',
            'семья': 'relationship',
            'family': 'relationship',
            'здоровье': 'health',
            'health': 'health',
            'финансы': 'finance',
            'finance': 'finance',
            'деньги': 'finance',
            'money': 'finance',
            'духовность': 'spiritual',
            'spiritual': 'spiritual',
            'астрология': 'astrology',
            'astrology': 'astrology',
            'конфликт': 'conflict',
            'conflict': 'conflict',
            'решение': 'decision',
            'decision': 'decision',
            'достижение': 'achievement',
            'achievement': 'achievement',
            'успех': 'achievement',
            'success': 'achievement'
        }
        
        # Ищем приоритетный тег
        for tag in tags_lower:
            if tag in priority_tags:
                return priority_tags[tag]
        
        # Если нет приоритетного тега, используем категорию
        if category_key != 'general':
            return category_key
        
        # Если нет категории, анализируем содержимое
        if entry.event_description:
            desc_lower = entry.event_description.lower()
            # Расширенный анализ ключевых слов
            keyword_mapping = {
                'work': ['работа', 'карьера', 'work', 'career', 'профессия', 'профессия'],
                'relationship': ['отношения', 'relationship', 'семья', 'family', 'любовь', 'love'],
                'health': ['здоровье', 'health', 'болезнь', 'illness', 'лечение', 'treatment'],
                'finance': ['финансы', 'finance', 'деньги', 'money', 'богатство', 'wealth']
            }
            
            for key, keywords in keyword_mapping.items():
                if any(keyword in desc_lower for keyword in keywords):
                    return key
        
        return 'general'
    
    def _analyze_frequency(
        self,
        clusters: Dict[str, List[ContextEntry]],
        all_entries: List[ContextEntry]
    ) -> Dict[str, Dict[str, Any]]:
        """Анализ частотности событий"""
        frequency_analysis = {}
        
        for cluster_key, cluster_entries in clusters.items():
            if len(cluster_entries) < self.config.PATTERNS_MIN_FREQUENCY:
                continue
            
            # Подсчитываем частоту по времени
            time_periods = self._group_by_time_periods(cluster_entries)
            
            # Анализируем теги
            tag_counts = Counter()
            for entry in cluster_entries:
                if entry.tags:
                    tag_counts.update(entry.tags)
            
            # Анализируем эмоциональные состояния
            emotion_counts = Counter()
            for entry in cluster_entries:
                if entry.emotional_state:
                    emotion_counts[entry.emotional_state] += 1
            
            frequency_analysis[cluster_key] = {
                'count': len(cluster_entries),
                'time_periods': time_periods,
                'tag_counts': dict(tag_counts),
                'emotion_counts': dict(emotion_counts),
                'entries': cluster_entries
            }
        
        return frequency_analysis
    
    def _group_by_time_periods(self, entries: List[ContextEntry]) -> Dict[str, int]:
        """Группировка событий по временным периодам"""
        periods = defaultdict(int)
        
        for entry in entries:
            # Группируем по месяцам
            period_key = entry.created_at.strftime('%Y-%m')
            periods[period_key] += 1
        
        return dict(periods)
    
    def _analyze_temporal_patterns(
        self,
        entries: List[ContextEntry]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Анализ временных паттернов: сезонность, цикличность
        
        ПРИМЕЧАНИЕ О ПРОИЗВОДИТЕЛЬНОСТИ:
        Временной анализ может быть тяжелым для больших объемов данных (>10k записей).
        Рекомендуется:
        1. Кэшировать результаты временного анализа
        2. Выполнять анализ в фоновых задачах для больших объемов
        3. Использовать предварительно рассчитанные паттерны из таблицы user_patterns
        
        Args:
            entries: Список событий для анализа
            
        Returns:
            Словарь с временными паттернами
        """
        temporal_patterns = {}
        
        if not entries or len(entries) < self.config.PATTERNS_MIN_FREQUENCY:
            return temporal_patterns
        
        # 1. Анализ сезонности (если включен)
        if self.config.PATTERNS_SEASONALITY_ENABLED:
            seasonal_patterns = self._detect_seasonality(entries)
            temporal_patterns.update(seasonal_patterns)
        
        # 2. Анализ цикличности
        cyclic_patterns = self._detect_cyclicity(entries)
        temporal_patterns.update(cyclic_patterns)
        
        # 3. Анализ дней недели
        weekday_patterns = self._detect_weekday_patterns(entries)
        temporal_patterns.update(weekday_patterns)
        
        return temporal_patterns
    
    def _detect_seasonality(self, entries: List[ContextEntry]) -> Dict[str, Dict[str, Any]]:
        """Выявление сезонных паттернов"""
        seasonal_patterns = {}
        
        # Группируем по месяцам
        monthly_counts = defaultdict(int)
        for entry in entries:
            month = entry.created_at.month
            monthly_counts[month] += 1
        
        # Ищем месяцы с повышенной активностью
        if monthly_counts:
            avg_count = sum(monthly_counts.values()) / len(monthly_counts)
            for month, count in monthly_counts.items():
                if count >= avg_count * 1.5:  # На 50% выше среднего
                    month_names = {
                        1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
                        5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
                        9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
                    }
                    pattern_key = f"seasonal_{month}"
                    seasonal_patterns[pattern_key] = {
                        'type': 'seasonal',
                        'month': month,
                        'month_name': month_names.get(month, f'месяц_{month}'),
                        'frequency': count,
                        'description': f"Повышенная активность в {month_names.get(month, f'месяце {month}')}"
                    }
        
        return seasonal_patterns
    
    def _detect_cyclicity(self, entries: List[ContextEntry]) -> Dict[str, Dict[str, Any]]:
        """Выявление циклических паттернов"""
        cyclic_patterns = {}
        
        if len(entries) < 3:
            return cyclic_patterns
        
        # Сортируем по дате
        sorted_entries = sorted(entries, key=lambda e: e.created_at)
        
        # Анализируем интервалы между событиями
        intervals = []
        for i in range(1, len(sorted_entries)):
            interval_days = (sorted_entries[i].created_at - sorted_entries[i-1].created_at).days
            if interval_days >= self.config.PATTERNS_MIN_CYCLIC_INTERVAL_DAYS:
                intervals.append(interval_days)
        
        if not intervals:
            return cyclic_patterns
        
        # Ищем повторяющиеся интервалы
        interval_counts = Counter(intervals)
        common_intervals = [
            (interval, count) 
            for interval, count in interval_counts.items() 
            if count >= 2  # Минимум 2 повторения
        ]
        
        for interval, count in common_intervals:
            pattern_key = f"cyclic_{interval}_days"
            cyclic_patterns[pattern_key] = {
                'type': 'cyclic',
                'interval_days': interval,
                'frequency': count,
                'description': f"Циклический паттерн: события повторяются каждые {interval} дней"
            }
        
        return cyclic_patterns
    
    def _detect_weekday_patterns(self, entries: List[ContextEntry]) -> Dict[str, Dict[str, Any]]:
        """Выявление паттернов по дням недели"""
        weekday_patterns = {}
        
        weekday_counts = defaultdict(int)
        for entry in entries:
            weekday = entry.created_at.weekday()  # 0 = понедельник, 6 = воскресенье
            weekday_counts[weekday] += 1
        
        if weekday_counts:
            avg_count = sum(weekday_counts.values()) / len(weekday_counts)
            weekday_names = {
                0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг',
                4: 'пятница', 5: 'суббота', 6: 'воскресенье'
            }
            
            for weekday, count in weekday_counts.items():
                if count >= avg_count * 1.3:  # На 30% выше среднего
                    pattern_key = f"weekday_{weekday}"
                    weekday_patterns[pattern_key] = {
                        'type': 'weekday',
                        'weekday': weekday,
                        'weekday_name': weekday_names.get(weekday, f'день_{weekday}'),
                        'frequency': count,
                        'description': f"Повышенная активность по {weekday_names.get(weekday, f'дню {weekday}')}"
                    }
        
        return weekday_patterns
    
    def _identify_patterns(
        self,
        frequency_analysis: Dict[str, Dict[str, Any]],
        clusters: Dict[str, List[ContextEntry]],
        all_entries: List[ContextEntry],
        temporal_patterns: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Pattern]:
        """Выявление паттернов"""
        patterns = []
        
        for cluster_key, analysis in frequency_analysis.items():
            count = analysis['count']
            
            # Проверяем минимальную частоту
            if count < self.config.PATTERNS_MIN_FREQUENCY:
                continue
            
            # Рассчитываем значимость паттерна (улучшенный расчет)
            significance_score = self._calculate_pattern_significance(
                analysis, 
                temporal_patterns or {}
            )
            
            # Проверяем наличие временных паттернов для этого кластера
            temporal_info = None
            if temporal_patterns:
                # Ищем связанные временные паттерны (упрощенная логика)
                # В реальной реализации можно использовать более сложное сопоставление
                for pattern_key, pattern_data in temporal_patterns.items():
                    if pattern_data.get('frequency', 0) >= count * 0.5:  # Если частота сопоставима
                        temporal_info = pattern_data
                        break
            
            # Формируем описание паттерна
            description = self._generate_pattern_description(
                cluster_key, 
                analysis,
                temporal_info
            )
            
            # Преобразуем записи в SelectedEvent
            selected_events = []
            for entry in analysis['entries'][:10]:  # Берем первые 10 событий
                try:
                    category = determine_event_category(entry)
                    event = SelectedEvent(
                        id=entry.id,
                        text=format_event_text(entry),
                        date=entry.created_at,
                        significance_score=1.0,
                        category=category,
                        tags=entry.tags if entry.tags else [],
                        source='patterns_module'
                    )
                    selected_events.append(event)
                except Exception as e:
                    logger.error(f"Ошибка создания SelectedEvent для entry {entry.id}: {str(e)}", exc_info=True)
                    continue
            
            pattern = Pattern(
                theme=cluster_key,
                frequency=count,
                events=selected_events,
                description=description,
                significance_score=significance_score
            )
            patterns.append(pattern)
        
        return patterns
    
    def _calculate_pattern_significance(
        self, 
        analysis: Dict[str, Any],
        temporal_patterns: Dict[str, Dict[str, Any]] = None
    ) -> float:
        """
        Улучшенный расчет значимости паттерна
        
        Учитывает:
        - Частоту событий
        - Распределение по времени
        - Приоритет событий
        - Эмоциональную окраску
        - Временные паттерны (сезонность, цикличность)
        """
        count = analysis['count']
        time_periods = analysis['time_periods']
        entries = analysis.get('entries', [])
        
        # 1. Базовая значимость на основе частоты
        frequency_score = min(1.0, count / 10.0)  # Нормализуем к 1.0
        
        # 2. Значимость на основе распределения по времени
        period_count = len(time_periods)
        time_distribution_score = min(1.0, period_count / 12.0)  # Нормализуем к 1.0
        
        # 3. Значимость на основе приоритета событий
        priority_scores = []
        for entry in entries:
            if entry.priority:
                priority_scores.append(entry.priority / 5.0)  # Нормализуем к 1.0
        
        priority_score = (
            sum(priority_scores) / len(priority_scores) 
            if priority_scores else 0.5
        )
        
        # 4. Значимость на основе эмоциональной окраски
        emotion_counts = analysis.get('emotion_counts', {})
        emotional_score = 0.5  # По умолчанию нейтральная
        
        if emotion_counts:
            # Высокая значимость если есть доминирующая эмоция
            total_emotions = sum(emotion_counts.values())
            if total_emotions > 0:
                max_emotion_count = max(emotion_counts.values())
                emotional_score = max_emotion_count / total_emotions
        
        # 5. Бонус за временные паттерны
        temporal_bonus = 0.0
        if temporal_patterns:
            # Если есть временные паттерны, увеличиваем значимость
            temporal_bonus = min(0.2, len(temporal_patterns) * 0.1)
        
        # Комбинированная значимость с настраиваемыми весами
        scores = [
            frequency_score,
            time_distribution_score,
            priority_score,
            emotional_score
        ]
        
        weights = [
            self.config.PATTERNS_FREQUENCY_WEIGHT,
            self.config.PATTERNS_TIME_DISTRIBUTION_WEIGHT,
            self.config.PATTERNS_PRIORITY_WEIGHT,
            self.config.PATTERNS_EMOTIONAL_WEIGHT
        ]
        
        significance = combine_scores(scores, weights)
        
        # Добавляем бонус за временные паттерны
        significance = min(1.0, significance + temporal_bonus)
        
        return max(0.0, min(1.0, significance))
    
    def _generate_pattern_description(
        self,
        cluster_key: str,
        analysis: Dict[str, Any],
        temporal_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Генерация описания паттерна с учетом временных паттернов"""
        count = analysis['count']
        tag_counts = analysis.get('tag_counts', {})
        emotion_counts = analysis.get('emotion_counts', {})
        time_periods = analysis.get('time_periods', {})
        
        # Формируем описание
        description_parts = [f"Тема '{cluster_key}' встречается {count} раз"]
        
        # Добавляем информацию о временных паттернах
        if temporal_info:
            if temporal_info.get('type') == 'seasonal':
                description_parts.append(
                    f"Сезонный паттерн: {temporal_info.get('description', '')}"
                )
            elif temporal_info.get('type') == 'cyclic':
                description_parts.append(
                    f"Циклический паттерн: {temporal_info.get('description', '')}"
                )
            elif temporal_info.get('type') == 'weekday':
                description_parts.append(
                    f"Паттерн по дням недели: {temporal_info.get('description', '')}"
                )
        
        # Информация о распределении по времени
        if time_periods:
            period_count = len(time_periods)
            if period_count > 1:
                description_parts.append(f"Распределено по {period_count} временным периодам")
        
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_tags:
                tags_text = ", ".join([tag for tag, _ in top_tags])
                description_parts.append(f"Основные теги: {tags_text}")
        
        if emotion_counts:
            top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            if top_emotions:
                emotions_text = ", ".join([emotion for emotion, _ in top_emotions])
                description_parts.append(f"Преобладающие эмоции: {emotions_text}")
        
        return ". ".join(description_parts)
    

