"""
Система интеллектуального отбора контекста для формирования оптимальных промтов LLM.

Модули:
- module_freshness: Приоритет свежести событий
- module_emotions: Эмоциональные маркеры
- module_patterns: Паттерны повторения
- module_karma: Кармические узлы
- module_contacts: Контекстные связи и синастрии (2 этап)
- integrator: Формирование контекстного промта
"""

from app.services.context_selection.integrator import ContextIntegrator
from app.services.context_selection.module_freshness import FreshnessModule
from app.services.context_selection.module_emotions import EmotionsModule
from app.services.context_selection.module_patterns import PatternsModule
from app.services.context_selection.module_karma import KarmaModule
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.models import (
    ContextSelectionRequest,
    ContextSelectionResult,
    FreshnessResult,
    EmotionsResult,
    PatternsResult,
    KarmaResult,
    SelectedEvent
)

__all__ = [
    'ContextIntegrator',
    'FreshnessModule',
    'EmotionsModule',
    'PatternsModule',
    'KarmaModule',
    'ContextSelectionConfig',
    'ContextSelectionRequest',
    'ContextSelectionResult',
    'FreshnessResult',
    'EmotionsResult',
    'PatternsResult',
    'KarmaResult',
    'SelectedEvent',
]

