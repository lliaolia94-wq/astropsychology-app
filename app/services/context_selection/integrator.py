"""
ИНТЕГРАЦИОННЫЙ МОДУЛЬ: ФОРМИРОВАНИЕ КОНТЕКСТНОГО ПРОМТА

Назначение: Объединение выходных данных всех модулей в единый оптимизированный промт.

Алгоритм работы:
1. Сбор данных: получение выходных данных от всех модулей
2. Приоритизация: определение наиболее важных элементов контекста
3. Структурирование: компоновка данных по установленному шаблону
4. Оптимизация объема: контроль итогового размера контекста (исключение избыточности)
"""
import logging
from typing import List, Dict, Any, Optional, Set, Callable
from datetime import datetime, timezone

from app.services.context_selection.models import (
    ContextSelectionRequest,
    ContextSelectionResult,
    SelectedEvent,
    Pattern,
    EmotionsResult,
    KarmaResult,
    FreshnessResult,
    PatternsResult
)
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.module_freshness import FreshnessModule
from app.services.context_selection.module_emotions import EmotionsModule
from app.services.context_selection.module_patterns import PatternsModule
from app.services.context_selection.module_karma import KarmaModule
from app.services.context_selection.utils import (
    remove_duplicates, estimate_tokens, truncate_text, safe_execute
)
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class ContextIntegrator:
    """Интеграционный модуль для формирования контекстного промта"""
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
        self.freshness_module = FreshnessModule(config)
        self.emotions_module = EmotionsModule(config)
        self.patterns_module = PatternsModule(config)
        self.karma_module = KarmaModule(config)
    
    def build_context_prompt(
        self,
        request: ContextSelectionRequest,
        db
    ) -> ContextSelectionResult:
        """
        Формирование контекстного промта
        
        Args:
            request: Запрос на отбор контекста
            db: Сессия БД
            
        Returns:
            ContextSelectionResult с готовым промтом
        """
        start_time = datetime.now()
        
        logger.info(f"Начало формирования контекстного промта для пользователя {request.user_id}")
        
        # 1. Сбор данных: получение выходных данных от всех модулей
        
        # Получаем семантические оценки релевантности ОДИН РАЗ для всех модулей
        similarity_scores = {}
        vector_results_cache = []
        
        if self.config.ENABLE_VECTOR_SEARCH and vector_service.client:
            try:
                vector_results_cache = vector_service.search_similar(
                    query_text=request.current_query,
                    user_id=request.user_id,
                    limit=50,
                    score_threshold=self.config.VECTOR_SEARCH_SCORE_THRESHOLD
                )
                similarity_scores = {
                    result['payload'].get('entry_id'): result['score']
                    for result in vector_results_cache
                    if result['payload'].get('entry_id')
                }
                logger.info(f"Векторный поиск: найдено {len(vector_results_cache)} результатов")
            except Exception as e:
                logger.error(f"Ошибка векторного поиска: {str(e)}", exc_info=True)
                # Продолжаем работу без векторного поиска
        
        # МОДУЛЬ 1: Приоритет свежести
        period_days = request.period_days or self.config.FRESHNESS_DEFAULT_PERIOD_DAYS
        limit = request.limit or self.config.FRESHNESS_DEFAULT_LIMIT
        
        freshness_result = self._safe_execute_module(
            module_name="freshness",
            func=lambda: self.freshness_module.select_relevant_events(
                db=db,
                user_id=request.user_id,
                period_days=period_days,
                limit=limit,
                current_query=request.current_query,
                similarity_scores=similarity_scores
            ),
            fallback=FreshnessResult(
                events=[],
                total_processed=0,
                period_days=period_days,
                processing_time_ms=0.0
            )
        )
        logger.info(f"Модуль свежести: отобрано {len(freshness_result.events)} событий")
        
        # МОДУЛЬ 2: Эмоциональные маркеры
        emotions_result = EmotionsResult(
            dominant_emotion=None,
            relevant_events=[],
            emotional_pattern=None,
            processing_time_ms=0.0
        )
        
        if request.include_emotions:
            emotions_result = self._safe_execute_module(
                module_name="emotions",
                func=lambda: self.emotions_module.detect_emotions(
                    query_text=request.current_query,
                    db=db,
                    user_id=request.user_id,
                    current_events=freshness_result.events,
                    vector_results_cache=vector_results_cache  # Переиспользуем результаты
                ),
                fallback=emotions_result
            )
            logger.info(f"Модуль эмоций: найдено {len(emotions_result.relevant_events)} событий")
        
        # МОДУЛЬ 3: Паттерны повторения
        patterns_result = PatternsResult(
            patterns=[],
            total_patterns_found=0,
            processing_time_ms=0.0
        )
        
        if request.include_patterns:
            patterns_result = self._safe_execute_module(
                module_name="patterns",
                func=lambda: self.patterns_module.detect_patterns(
                    db=db,
                    user_id=request.user_id,
                    current_query=request.current_query,
                    history_years=self.config.MAX_HISTORY_YEARS,
                    vector_results_cache=vector_results_cache  # Переиспользуем результаты
                ),
                fallback=patterns_result
            )
            logger.info(f"Модуль паттернов: найдено {len(patterns_result.patterns)} паттернов")
        
        # МОДУЛЬ 4: Кармические узлы
        karma_result = KarmaResult(
            themes=[],
            active_themes_count=0,
            processing_time_ms=0.0
        )
        
        if request.include_karma:
            karma_result = self._safe_execute_module(
                module_name="karma",
                func=lambda: self.karma_module.identify_karmic_themes(
                    db=db,
                    user_id=request.user_id,
                    user_profile=request.user_profile,
                    current_query=request.current_query,
                    history_years=self.config.MAX_HISTORY_YEARS,
                    vector_results_cache=vector_results_cache  # Переиспользуем результаты
                ),
                fallback=karma_result
            )
            logger.info(f"Модуль кармы: найдено {len(karma_result.themes)} тем")
        
        # 2. Приоритизация: определение наиболее важных элементов контекста
        relevant_history = self._prioritize_events(
            freshness_result.events,
            emotions_result.relevant_events,
            patterns_result.patterns,
            karma_result.themes
        )
        
        # 3. Структурирование: компоновка данных по установленному шаблону
        formatted_prompt = self._format_prompt(
            user_profile=request.user_profile or {},
            current_query=request.current_query,
            relevant_history=relevant_history,
            patterns=patterns_result.patterns,
            emotions_result=emotions_result,
            karma_result=karma_result
        )
        
        # 4. Оптимизация объема: контроль итогового размера контекста
        total_tokens = estimate_tokens(formatted_prompt)
        
        if total_tokens > self.config.INTEGRATOR_MAX_TOKENS:
            logger.warning(f"Промт превышает лимит токенов: {total_tokens} > {self.config.INTEGRATOR_MAX_TOKENS}")
            formatted_prompt = truncate_text(formatted_prompt, self.config.INTEGRATOR_MAX_TOKENS)
            total_tokens = estimate_tokens(formatted_prompt)
        
        # Анализ текущей ситуации
        current_situation = self._analyze_current_situation(
            request.current_query,
            emotions_result.dominant_emotion
        )
        
        # Вычисляем время обработки
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Контекстный промт сформирован за {processing_time_ms:.2f} мс ({total_tokens} токенов)")
        
        return ContextSelectionResult(
            user_profile=request.user_profile or {},
            current_situation=current_situation,
            relevant_history=relevant_history,
            pattern_insights=patterns_result.patterns,
            emotional_context=emotions_result,
            karmic_context=karma_result,
            formatted_prompt=formatted_prompt,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms
        )
    
    def _prioritize_events(
        self,
        freshness_events: List[SelectedEvent],
        emotions_events: List[SelectedEvent],
        patterns: List[Pattern],
        karma_themes: List
    ) -> List[SelectedEvent]:
        """Приоритизация событий из всех модулей"""
        # Объединяем события из всех модулей
        all_events = []
        
        # События из модуля свежести (высокий приоритет)
        for event in freshness_events:
            event.significance_score *= 1.2  # Повышаем значимость
            all_events.append(event)
        
        # События из модуля эмоций
        for event in emotions_events:
            # Проверяем, не дубликат ли это
            if not any(e.id == event.id for e in all_events):
                event.significance_score *= 1.1  # Немного повышаем значимость
                all_events.append(event)
        
        # События из паттернов
        for pattern in patterns:
            for event in pattern.events:
                if not any(e.id == event.id for e in all_events):
                    event.significance_score *= 1.05  # Небольшое повышение
                    all_events.append(event)
        
        # События из кармических тем
        for theme in karma_themes:
            for event in theme.confirmed_events:
                if not any(e.id == event.id for e in all_events):
                    event.significance_score *= theme.manifestation_level  # Учитываем уровень проявления
                    all_events.append(event)
        
        # Удаляем дубликаты
        unique_events = remove_duplicates(
            [{'id': e.id, 'event': e} for e in all_events],
            key_field='id'
        )
        
        # Сортируем по значимости
        events = [item['event'] for item in unique_events]
        events.sort(key=lambda e: e.significance_score, reverse=True)
        
        # Ограничиваем количество (3-7 событий согласно ТЗ)
        max_events = min(7, len(events))
        return events[:max_events]
    
    def _analyze_current_situation(
        self,
        current_query: str,
        dominant_emotion: Optional[Any]
    ) -> str:
        """Анализ текущей ситуации"""
        situation_parts = [f"Текущий запрос: {current_query}"]
        
        if dominant_emotion:
            situation_parts.append(f"Доминирующая эмоция: {dominant_emotion.value}")
        
        return ". ".join(situation_parts)
    
    def _format_prompt(
        self,
        user_profile: Dict[str, Any],
        current_query: str,
        relevant_history: List[SelectedEvent],
        patterns: List[Pattern],
        emotions_result: EmotionsResult,
        karma_result: KarmaResult
    ) -> str:
        """Форматирование промта по установленному шаблону"""
        prompt_parts = []
        
        # USER_PROFILE: ключевые неизменные данные
        prompt_parts.append("USER_PROFILE:")
        if user_profile:
            profile_items = []
            if user_profile.get('name'):
                profile_items.append(f"Имя: {user_profile['name']}")
            if user_profile.get('sun_sign'):
                profile_items.append(f"Солнечный знак: {user_profile['sun_sign']}")
            if user_profile.get('moon_sign'):
                profile_items.append(f"Знак луны: {user_profile['moon_sign']}")
            if user_profile.get('ascendant_sign'):
                profile_items.append(f"Асцендент: {user_profile['ascendant_sign']}")
            
            if profile_items:
                prompt_parts.append("\n".join(profile_items))
            else:
                prompt_parts.append("Данные профиля не указаны")
        else:
            prompt_parts.append("Данные профиля не указаны")
        
        # CURRENT_SITUATION: анализ текущего запроса
        prompt_parts.append("\nCURRENT_SITUATION:")
        situation_parts = [f"Запрос: {current_query}"]
        
        if emotions_result.dominant_emotion:
            situation_parts.append(f"Эмоция: {emotions_result.dominant_emotion.value}")
        
        if emotions_result.emotional_pattern:
            situation_parts.append(f"Эмоциональный паттерн: {emotions_result.emotional_pattern}")
        
        prompt_parts.append(". ".join(situation_parts))
        
        # RELEVANT_HISTORY: 3-7 самых релевантных событий
        prompt_parts.append("\nRELEVANT_HISTORY:")
        if relevant_history:
            for i, event in enumerate(relevant_history, 1):
                event_text = f"{i}. {event.text}"
                if event.date:
                    event_text += f" ({event.date.strftime('%Y-%m-%d')})"
                if event.emotional_state:
                    event_text += f" [Эмоция: {event.emotional_state.value}]"
                if event.tags:
                    event_text += f" [Теги: {', '.join(event.tags[:3])}]"
                prompt_parts.append(event_text)
        else:
            prompt_parts.append("Релевантная история не найдена")
        
        # PATTERN_INSIGHTS: выявленные циклы и паттерны
        prompt_parts.append("\nPATTERN_INSIGHTS:")
        if patterns:
            for i, pattern in enumerate(patterns, 1):
                pattern_text = f"{i}. {pattern.theme}: {pattern.description}"
                pattern_text += f" (встречается {pattern.frequency} раз)"
                prompt_parts.append(pattern_text)
        else:
            prompt_parts.append("Паттерны не выявлены")
        
        # EMOTIONAL_CONTEXT: эмоциональная динамика
        prompt_parts.append("\nEMOTIONAL_CONTEXT:")
        if emotions_result.dominant_emotion:
            prompt_parts.append(f"Доминирующая эмоция: {emotions_result.dominant_emotion.value}")
        
        if emotions_result.relevant_events:
            prompt_parts.append(f"Найдено {len(emotions_result.relevant_events)} эмоционально релевантных событий")
        else:
            prompt_parts.append("Эмоциональный контекст не определен")
        
        # KARMIC_CONTEXT: кармические темы
        prompt_parts.append("\nKARMIC_CONTEXT:")
        if karma_result.themes:
            for i, theme in enumerate(karma_result.themes, 1):
                theme_text = f"{i}. {theme.theme}: {theme.description}"
                theme_text += f" (уровень проявления: {theme.manifestation_level:.2f})"
                prompt_parts.append(theme_text)
        else:
            prompt_parts.append("Кармические темы не выявлены")
        
        return "\n\n".join(prompt_parts)
    
    def _safe_execute_module(
        self,
        module_name: str,
        func: Callable,
        fallback: Any
    ) -> Any:
        """
        Безопасное выполнение модуля с обработкой ошибок
        
        Args:
            module_name: Название модуля для логирования
            func: Функция для выполнения
            fallback: Значение по умолчанию при ошибке
            
        Returns:
            Результат функции или fallback при ошибке
        """
        return safe_execute(
            func=func,
            fallback=fallback,
            error_message=f"Ошибка в модуле {module_name}",
            log_error=True
        )

