"""
Конфигурация модулей интеллектуального отбора контекста
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class ContextSelectionConfig:
    """Конфигурация для системы интеллектуального отбора контекста"""
    
    # МОДУЛЬ 1: Приоритет свежести
    FRESHNESS_DEFAULT_PERIOD_DAYS = int(os.getenv("CONTEXT_FRESHNESS_PERIOD_DAYS", "30"))
    FRESHNESS_DEFAULT_LIMIT = int(os.getenv("CONTEXT_FRESHNESS_LIMIT", "7"))
    FRESHNESS_MAX_AGE_DAYS = int(os.getenv("CONTEXT_FRESHNESS_MAX_AGE_DAYS", "90"))
    FRESHNESS_DECAY_FACTOR = float(os.getenv("CONTEXT_FRESHNESS_DECAY_FACTOR", "0.1"))
    
    # Веса для комбинирования оценок (time, priority, similarity)
    FRESHNESS_TIME_WEIGHT = float(os.getenv("CONTEXT_FRESHNESS_TIME_WEIGHT", "0.5"))
    FRESHNESS_PRIORITY_WEIGHT = float(os.getenv("CONTEXT_FRESHNESS_PRIORITY_WEIGHT", "0.3"))
    FRESHNESS_SIMILARITY_WEIGHT = float(os.getenv("CONTEXT_FRESHNESS_SIMILARITY_WEIGHT", "0.2"))
    
    # Максимальное количество записей для обработки (пагинация)
    FRESHNESS_MAX_PROCESSING_LIMIT = int(os.getenv("CONTEXT_FRESHNESS_MAX_PROCESSING_LIMIT", "1000"))
    
    # МОДУЛЬ 2: Эмоциональные маркеры
    EMOTIONS_DETECTION_ENABLED = os.getenv("CONTEXT_EMOTIONS_ENABLED", "true").lower() == "true"
    EMOTIONS_SIMILARITY_THRESHOLD = float(os.getenv("CONTEXT_EMOTIONS_SIMILARITY_THRESHOLD", "0.6"))
    EMOTIONS_MAX_RESULTS = int(os.getenv("CONTEXT_EMOTIONS_MAX_RESULTS", "5"))
    
    # МОДУЛЬ 3: Паттерны повторения
    PATTERNS_ENABLED = os.getenv("CONTEXT_PATTERNS_ENABLED", "true").lower() == "true"
    PATTERNS_MIN_FREQUENCY = int(os.getenv("CONTEXT_PATTERNS_MIN_FREQUENCY", "3"))
    PATTERNS_MAX_RESULTS = int(os.getenv("CONTEXT_PATTERNS_MAX_RESULTS", "5"))
    PATTERNS_CLUSTERING_THRESHOLD = float(os.getenv("CONTEXT_PATTERNS_CLUSTERING_THRESHOLD", "0.7"))
    
    # Веса для расчета значимости паттернов
    PATTERNS_FREQUENCY_WEIGHT = float(os.getenv("CONTEXT_PATTERNS_FREQUENCY_WEIGHT", "0.4"))
    PATTERNS_TIME_DISTRIBUTION_WEIGHT = float(os.getenv("CONTEXT_PATTERNS_TIME_DISTRIBUTION_WEIGHT", "0.2"))
    PATTERNS_PRIORITY_WEIGHT = float(os.getenv("CONTEXT_PATTERNS_PRIORITY_WEIGHT", "0.2"))
    PATTERNS_EMOTIONAL_WEIGHT = float(os.getenv("CONTEXT_PATTERNS_EMOTIONAL_WEIGHT", "0.2"))
    
    # Настройки временных паттернов
    PATTERNS_TEMPORAL_ANALYSIS_ENABLED = os.getenv("CONTEXT_PATTERNS_TEMPORAL_ENABLED", "true").lower() == "true"
    PATTERNS_MIN_CYCLIC_INTERVAL_DAYS = int(os.getenv("CONTEXT_PATTERNS_MIN_CYCLIC_INTERVAL", "7"))  # Минимальный интервал для цикличности
    PATTERNS_SEASONALITY_ENABLED = os.getenv("CONTEXT_PATTERNS_SEASONALITY_ENABLED", "true").lower() == "true"
    
    # МОДУЛЬ 4: Кармические узлы
    KARMA_ENABLED = os.getenv("CONTEXT_KARMA_ENABLED", "true").lower() == "true"
    KARMA_SIMILARITY_THRESHOLD = float(os.getenv("CONTEXT_KARMA_SIMILARITY_THRESHOLD", "0.65"))
    KARMA_MAX_THEMES = int(os.getenv("CONTEXT_KARMA_MAX_THEMES", "5"))
    
    # Веса для расчета уровня проявления кармических тем
    KARMA_FREQUENCY_WEIGHT = float(os.getenv("CONTEXT_KARMA_FREQUENCY_WEIGHT", "0.3"))
    KARMA_PRIORITY_WEIGHT = float(os.getenv("CONTEXT_KARMA_PRIORITY_WEIGHT", "0.25"))
    KARMA_REPETITION_WEIGHT = float(os.getenv("CONTEXT_KARMA_REPETITION_WEIGHT", "0.2"))
    KARMA_ASPECT_WEIGHT = float(os.getenv("CONTEXT_KARMA_ASPECT_WEIGHT", "0.25"))  # Учет астрологических аспектов
    
    # Настройки кэширования натальных данных
    KARMA_CACHE_ENABLED = os.getenv("CONTEXT_KARMA_CACHE_ENABLED", "true").lower() == "true"
    KARMA_CACHE_TTL_SECONDS = int(os.getenv("CONTEXT_KARMA_CACHE_TTL", "3600"))  # 1 час по умолчанию
    
    # ИНТЕГРАЦИОННЫЙ МОДУЛЬ
    INTEGRATOR_MAX_TOKENS = int(os.getenv("CONTEXT_INTEGRATOR_MAX_TOKENS", "1500"))
    INTEGRATOR_MAX_TIME_SECONDS = int(os.getenv("CONTEXT_INTEGRATOR_MAX_TIME_SECONDS", "5"))
    INTEGRATOR_ENABLE_CACHING = os.getenv("CONTEXT_INTEGRATOR_CACHE", "true").lower() == "true"
    
    # Общие настройки
    MAX_HISTORY_YEARS = int(os.getenv("CONTEXT_MAX_HISTORY_YEARS", "3"))
    ENABLE_VECTOR_SEARCH = os.getenv("CONTEXT_VECTOR_SEARCH_ENABLED", "true").lower() == "true"
    VECTOR_SEARCH_SCORE_THRESHOLD = float(os.getenv("CONTEXT_VECTOR_SEARCH_THRESHOLD", "0.6"))
    
    @classmethod
    def get_module_config(cls, module_name: str) -> Dict[str, Any]:
        """Получить конфигурацию для конкретного модуля"""
        configs = {
            "freshness": {
                "period_days": cls.FRESHNESS_DEFAULT_PERIOD_DAYS,
                "limit": cls.FRESHNESS_DEFAULT_LIMIT,
                "max_age_days": cls.FRESHNESS_MAX_AGE_DAYS,
                "decay_factor": cls.FRESHNESS_DECAY_FACTOR,
                "time_weight": cls.FRESHNESS_TIME_WEIGHT,
                "priority_weight": cls.FRESHNESS_PRIORITY_WEIGHT,
                "similarity_weight": cls.FRESHNESS_SIMILARITY_WEIGHT,
                "max_processing_limit": cls.FRESHNESS_MAX_PROCESSING_LIMIT,
            },
            "emotions": {
                "enabled": cls.EMOTIONS_DETECTION_ENABLED,
                "similarity_threshold": cls.EMOTIONS_SIMILARITY_THRESHOLD,
                "max_results": cls.EMOTIONS_MAX_RESULTS,
            },
            "patterns": {
                "enabled": cls.PATTERNS_ENABLED,
                "min_frequency": cls.PATTERNS_MIN_FREQUENCY,
                "max_results": cls.PATTERNS_MAX_RESULTS,
                "clustering_threshold": cls.PATTERNS_CLUSTERING_THRESHOLD,
                "frequency_weight": cls.PATTERNS_FREQUENCY_WEIGHT,
                "time_distribution_weight": cls.PATTERNS_TIME_DISTRIBUTION_WEIGHT,
                "priority_weight": cls.PATTERNS_PRIORITY_WEIGHT,
                "emotional_weight": cls.PATTERNS_EMOTIONAL_WEIGHT,
                "temporal_analysis_enabled": cls.PATTERNS_TEMPORAL_ANALYSIS_ENABLED,
                "min_cyclic_interval_days": cls.PATTERNS_MIN_CYCLIC_INTERVAL_DAYS,
                "seasonality_enabled": cls.PATTERNS_SEASONALITY_ENABLED,
            },
            "karma": {
                "enabled": cls.KARMA_ENABLED,
                "similarity_threshold": cls.KARMA_SIMILARITY_THRESHOLD,
                "max_themes": cls.KARMA_MAX_THEMES,
                "frequency_weight": cls.KARMA_FREQUENCY_WEIGHT,
                "priority_weight": cls.KARMA_PRIORITY_WEIGHT,
                "repetition_weight": cls.KARMA_REPETITION_WEIGHT,
                "aspect_weight": cls.KARMA_ASPECT_WEIGHT,
                "cache_enabled": cls.KARMA_CACHE_ENABLED,
                "cache_ttl_seconds": cls.KARMA_CACHE_TTL_SECONDS,
            },
        }
        return configs.get(module_name, {})

