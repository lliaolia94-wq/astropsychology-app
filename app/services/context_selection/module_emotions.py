"""
МОДУЛЬ 2: ЭМОЦИОНАЛЬНЫЕ МАРКЕРЫ

Назначение: Выявление и учет эмоционального контекста текущего запроса и исторических событий.

Алгоритм работы:
1. Детекция эмоций: анализ текущего запроса на наличие эмоциональных маркеров
2. Векторизация эмоций: преобразование выявленных эмоций в эмбеддинги
3. Семантический поиск: поиск исторических событий с похожей эмоциональной окраской
4. Формирование эмоционального контекста: отбор 3-5 наиболее релевантных эмоционально схожих событий
"""
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.database.models import ContextEntry
from app.services.context_selection.models import (
    SelectedEvent, EmotionsResult, EmotionalState, EventCategory
)
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.utils import (
    timing_decorator, safe_execute, determine_event_category, format_event_text
)
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class EmotionsModule:
    """Модуль эмоциональных маркеров"""
    
    # Эмоциональный словарь (таксономия эмоций и их ключевые слова)
    EMOTION_KEYWORDS = {
        EmotionalState.JOY: ['радость', 'счастье', 'восторг', 'удовольствие', 'радуется', 'радуется', 'рад', 'joy', 'happy', 'pleasure'],
        EmotionalState.SADNESS: ['грусть', 'печаль', 'тоска', 'уныние', 'грустно', 'печально', 'sad', 'sadness', 'sorrow'],
        EmotionalState.ANGER: ['злость', 'гнев', 'ярость', 'раздражение', 'злой', 'разозлился', 'anger', 'angry', 'rage'],
        EmotionalState.FEAR: ['страх', 'боязнь', 'тревога', 'опасение', 'боюсь', 'страшно', 'fear', 'afraid', 'anxiety'],
        EmotionalState.SURPRISE: ['удивление', 'изумление', 'неожиданность', 'удивлен', 'surprise', 'surprised', 'amazed'],
        EmotionalState.CALM: ['спокойствие', 'умиротворение', 'расслабление', 'спокоен', 'calm', 'peaceful', 'relaxed'],
        EmotionalState.ANXIETY: ['тревога', 'беспокойство', 'волнение', 'тревожно', 'anxiety', 'worried', 'nervous'],
        EmotionalState.TENSION: ['напряжение', 'стресс', 'давление', 'напряжен', 'tension', 'stress', 'pressure'],
        EmotionalState.EXCITEMENT: ['волнение', 'возбуждение', 'энтузиазм', 'взволнован', 'excitement', 'excited', 'enthusiasm'],
        EmotionalState.CONFUSION: ['путаница', 'непонимание', 'растерянность', 'запутался', 'confusion', 'confused', 'bewildered'],
        EmotionalState.HOPE: ['надежда', 'ожидание', 'верю', 'hopе', 'hope', 'hopeful', 'expectation'],
        EmotionalState.DISAPPOINTMENT: ['разочарование', 'расстройство', 'разочарован', 'disappointment', 'disappointed', 'upset'],
    }
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
    
    def detect_emotions(
        self,
        query_text: str,
        db: Session,
        user_id: int,
        current_events: Optional[List[SelectedEvent]] = None,
        vector_results_cache: Optional[List[Dict[str, Any]]] = None
    ) -> EmotionsResult:
        """
        Детекция эмоций и поиск релевантных событий
        
        ПРИМЕЧАНИЕ: Текущая реализация использует детекцию по ключевым словам.
        В будущем рекомендуется использовать ML-модели для классификации эмоций
        (например, fine-tuned BERT для эмоциональной классификации).
        Это повысит точность детекции и позволит выявлять более сложные эмоциональные состояния.
        
        Args:
            query_text: Текущий запрос пользователя
            db: Сессия БД
            user_id: ID пользователя
            current_events: Список текущих событий (для фильтрации)
            
        Returns:
            EmotionsResult с доминирующей эмоцией и релевантными событиями
        """
        start_time = datetime.now()
        
        if not self.config.EMOTIONS_DETECTION_ENABLED:
            logger.info("Модуль эмоций отключен")
            return EmotionsResult(
                dominant_emotion=None,
                relevant_events=[],
                emotional_pattern=None,
                processing_time_ms=0.0
            )
        
        # 1. Детекция эмоций: анализ текущего запроса
        dominant_emotion = self._detect_dominant_emotion(query_text)
        
        logger.info(f"Выявлена доминирующая эмоция: {dominant_emotion}")
        
        # 2. Векторизация эмоций и семантический поиск
        relevant_events = []
        
        if dominant_emotion:
            try:
                # Используем кэш векторных результатов или выполняем новый поиск
                if vector_results_cache:
                    # Фильтруем результаты по порогу релевантности
                    vector_results = [
                        r for r in vector_results_cache
                        if r.get('score', 0) >= self.config.EMOTIONS_SIMILARITY_THRESHOLD
                    ]
                    logger.debug(f"Использован кэш векторных результатов: {len(vector_results)} записей")
                elif vector_service.client:
                    # Формируем запрос для векторного поиска с учетом эмоции
                    emotion_query = self._build_emotion_query(query_text, dominant_emotion)
                    
                    # 3. Семантический поиск: поиск исторических событий с похожей эмоциональной окраской
                    vector_results = vector_service.search_similar(
                        query_text=emotion_query,
                        user_id=user_id,
                        limit=self.config.EMOTIONS_MAX_RESULTS * 2,  # Берем больше для фильтрации
                        score_threshold=self.config.EMOTIONS_SIMILARITY_THRESHOLD
                    )
                else:
                    vector_results = []
                
                # Получаем записи из БД пакетным запросом (избегаем N+1)
                entry_ids = [result['payload'].get('entry_id') for result in vector_results if result['payload'].get('entry_id')]
                
                if entry_ids:
                    # Пакетный запрос для избежания N+1 проблем
                    try:
                        entries = db.query(ContextEntry).filter(
                            ContextEntry.id.in_(entry_ids),
                            ContextEntry.user_id == user_id
                        ).all()
                    except Exception as e:
                        logger.error(f"Ошибка запроса к БД в модуле эмоций: {str(e)}", exc_info=True)
                        entries = []
                    
                    # Создаем словарь для быстрого доступа
                    entry_dict = {entry.id: entry for entry in entries}
                    
                    # Формируем список релевантных событий
                    current_event_ids = {e.id for e in current_events} if current_events else set()
                    
                    for result in vector_results:
                        entry_id = result['payload'].get('entry_id')
                        if not entry_id or entry_id not in entry_dict:
                            continue
                        
                        # Проверяем, не является ли это событие уже в current_events
                        if entry_id in current_event_ids:
                            continue
                        
                        try:
                            entry = entry_dict[entry_id]
                            similarity_score = result.get('score', 0.0)
                            
                            # Определяем эмоциональное состояние записи
                            entry_emotion = None
                            if entry.emotional_state:
                                try:
                                    entry_emotion = EmotionalState(entry.emotional_state.lower())
                                except ValueError:
                                    pass
                            
                            # Формируем текст события (используем общую утилиту)
                            event_text = format_event_text(entry)
                            
                            event = SelectedEvent(
                                id=entry.id,
                                text=event_text,
                                date=entry.created_at,
                                significance_score=similarity_score,
                                category=determine_event_category(entry),
                                emotional_state=entry_emotion,
                                tags=entry.tags if entry.tags else [],
                                similarity_score=similarity_score,
                                source='emotions_module'
                            )
                            relevant_events.append(event)
                        except Exception as e:
                            logger.error(f"Ошибка обработки события {entry_id} в модуле эмоций: {str(e)}", exc_info=True)
                            continue
                            
            except Exception as e:
                logger.error(f"Ошибка в модуле эмоций при поиске событий: {str(e)}", exc_info=True)
                # Продолжаем работу с пустым списком событий
            
            # Сортируем по релевантности
            relevant_events.sort(key=lambda x: x.similarity_score or 0.0, reverse=True)
            
            # 4. Лимитирование: выбор топ-N событий
            relevant_events = relevant_events[:self.config.EMOTIONS_MAX_RESULTS]
        
        # Определяем эмоциональный паттерн
        emotional_pattern = self._detect_emotional_pattern(relevant_events, dominant_emotion)
        
        # Вычисляем время обработки
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Найдено {len(relevant_events)} эмоционально релевантных событий за {processing_time_ms:.2f} мс")
        
        return EmotionsResult(
            dominant_emotion=dominant_emotion,
            relevant_events=relevant_events,
            emotional_pattern=emotional_pattern,
            processing_time_ms=processing_time_ms
        )
    
    def _detect_dominant_emotion(self, text: str) -> Optional[EmotionalState]:
        """Детекция доминирующей эмоции в тексте"""
        text_lower = text.lower()
        emotion_scores = {}
        
        # Подсчитываем совпадения ключевых слов для каждой эмоции
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return None
        
        # Возвращаем эмоцию с наибольшим счетом
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        return dominant_emotion
    
    def _build_emotion_query(self, query_text: str, emotion: EmotionalState) -> str:
        """
        Построение запроса для векторного поиска с учетом эмоции
        
        ПРИМЕЧАНИЕ: Текущая реализация добавляет ключевые слова эмоций к запросу,
        что может исказить семантический поиск. В будущем рекомендуется:
        1. Использовать отдельные эмоциональные эмбеддинги (emotion_vector)
        2. Выполнять гибридный поиск: семантический + эмоциональный
        3. Использовать фильтрацию по эмоциональным метаданным вместо модификации запроса
        """
        # Добавляем ключевые слова эмоции к запросу для улучшения поиска
        # TODO: Заменить на поиск по эмоциональным эмбеддингам
        emotion_keywords = self.EMOTION_KEYWORDS.get(emotion, [])
        emotion_text = " ".join(emotion_keywords[:3])  # Берем первые 3 ключевых слова
        
        return f"{query_text} {emotion_text}"
    
    def _detect_emotional_pattern(
        self,
        events: List[SelectedEvent],
        dominant_emotion: Optional[EmotionalState]
    ) -> Optional[str]:
        """Выявление эмоционального паттерна"""
        if not events or not dominant_emotion:
            return None
        
        # Подсчитываем частоту эмоций в релевантных событиях
        emotion_counts = {}
        for event in events:
            if event.emotional_state:
                emotion_counts[event.emotional_state] = emotion_counts.get(event.emotional_state, 0) + 1
        
        # Если есть повторяющаяся эмоция, формируем паттерн
        if emotion_counts:
            most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            frequency = emotion_counts[most_common_emotion]
            
            if frequency >= 2:
                return f"Повторяющаяся эмоция: {most_common_emotion.value} (встречается {frequency} раз)"
        
        return None
    

