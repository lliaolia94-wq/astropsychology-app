"""
Модели данных для системы интеллектуального отбора контекста
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class EventCategory(str, Enum):
    """Категории событий"""
    CONFLICT = "conflict"
    DECISION = "decision"
    ACHIEVEMENT = "achievement"
    RELATIONSHIP = "relationship"
    HEALTH = "health"
    FINANCE = "finance"
    SPIRITUAL = "spiritual"
    ASTROLOGY = "astrology"
    GENERAL = "general"


class EmotionalState(str, Enum):
    """Эмоциональные состояния"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    CALM = "calm"
    ANXIETY = "anxiety"
    TENSION = "tension"
    EXCITEMENT = "excitement"
    CONFUSION = "confusion"
    HOPE = "hope"
    DISAPPOINTMENT = "disappointment"


@dataclass
class SelectedEvent:
    """Выбранное событие с метаданными"""
    id: int
    text: str
    date: datetime
    significance_score: float
    category: EventCategory
    emotional_state: Optional[EmotionalState] = None
    tags: List[str] = field(default_factory=list)
    similarity_score: Optional[float] = None
    source: str = "unknown"  # current_session, semantic_search, critical_important, etc.


@dataclass
class FreshnessResult:
    """Результат модуля приоритета свежести"""
    events: List[SelectedEvent]
    total_processed: int
    period_days: int
    processing_time_ms: float


@dataclass
class EmotionsResult:
    """Результат модуля эмоциональных маркеров"""
    dominant_emotion: Optional[EmotionalState]
    relevant_events: List[SelectedEvent]
    emotional_pattern: Optional[str]
    processing_time_ms: float


@dataclass
class Pattern:
    """Выявленный паттерн"""
    theme: str
    frequency: int
    events: List[SelectedEvent]
    description: str
    significance_score: float


@dataclass
class PatternsResult:
    """Результат модуля паттернов повторения"""
    patterns: List[Pattern]
    total_patterns_found: int
    processing_time_ms: float


@dataclass
class KarmicTheme:
    """Кармическая тема"""
    theme: str
    manifestation_level: float  # 0.0 - 1.0
    confirmed_events: List[SelectedEvent]
    description: str
    source: str  # natal_chart, manual_marker, detected


@dataclass
class KarmaResult:
    """Результат модуля кармических узлов"""
    themes: List[KarmicTheme]
    active_themes_count: int
    processing_time_ms: float


@dataclass
class ContextSelectionRequest:
    """Запрос на отбор контекста"""
    user_id: int
    current_query: str
    current_query_metadata: Optional[Dict[str, Any]] = None
    period_days: Optional[int] = None
    limit: Optional[int] = None
    include_emotions: bool = True
    include_patterns: bool = True
    include_karma: bool = True
    user_profile: Optional[Dict[str, Any]] = None


@dataclass
class ContextSelectionResult:
    """Результат интеллектуального отбора контекста"""
    user_profile: Dict[str, Any]
    current_situation: str
    relevant_history: List[SelectedEvent]
    pattern_insights: List[Pattern]
    emotional_context: EmotionsResult
    karmic_context: KarmaResult
    formatted_prompt: str
    total_tokens: int
    processing_time_ms: float

