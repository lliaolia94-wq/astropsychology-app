"""
МОДУЛЬ 4: КАРМИЧЕСКИЕ УЗЛЫ

Назначение: Идентификация и отслеживание сквозных кармических тем пользователя.

Алгоритм работы:
1. Инициализация тем: загрузка базовых кармических тем из профиля (с кэшированием)
2. Семантический мониторинг: постоянный поиск событий, релевантных кармическим темам
3. Подтверждение значимости: учет ручных маркеров и повторяемости тем
4. Актуализация списка: регулярное обновление списка активных кармических тем

ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ:
- Кэширование натальных данных для избежания повторных запросов
- Улучшенный расчет уровня проявления с учетом астрологических аспектов
- Настраиваемые веса для расчета значимости
- Обработка ошибок при работе с астрологическими данными

РЕКОМЕНДАЦИЯ ПО ОПТИМИЗАЦИИ БД:
Для больших объемов данных рекомендуется создать оптимизированные таблицы:
CREATE TABLE karmic_themes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    theme_name VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'natal_chart', 'detected', 'user_labeled'
    manifestation_level DECIMAL(3,2) NOT NULL,
    astrological_indicators JSONB, -- Планеты, аспекты, дома
    is_active BOOLEAN DEFAULT TRUE,
    first_detected TIMESTAMP DEFAULT NOW(),
    last_manifested TIMESTAMP,
    INDEX idx_user_karmic (user_id, manifestation_level DESC)
);

CREATE TABLE theme_manifestations (
    id SERIAL PRIMARY KEY,
    theme_id INTEGER REFERENCES karmic_themes(id),
    entry_id INTEGER NOT NULL,
    relevance_score DECIMAL(3,2) NOT NULL,
    manifestation_type VARCHAR(50), -- 'challenge', 'lesson', 'growth'
    INDEX idx_theme_manifestations (theme_id, relevance_score DESC)
);
Это позволит кэшировать кармические темы и ускорить их обнаружение.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.database.models import ContextEntry, User, NatalChart
from app.services.context_selection.models import (
    SelectedEvent, KarmaResult, KarmicTheme, EventCategory
)
from app.services.context_selection.config import ContextSelectionConfig
from app.services.context_selection.utils import (
    timing_decorator, determine_event_category, combine_scores, safe_execute,
    format_event_text
)
from app.services.vector_service import vector_service
from app.services.cache_service import natal_chart_cache

logger = logging.getLogger(__name__)


class KarmaModule:
    """Модуль кармических узлов"""
    
    # Базовые кармические темы (из натальной карты)
    KARMIC_THEMES = [
        'отношения', 'relationships', 'партнерство', 'partnership',
        'работа', 'work', 'карьера', 'career', 'профессия', 'profession',
        'здоровье', 'health', 'болезнь', 'illness',
        'финансы', 'finance', 'деньги', 'money',
        'семья', 'family', 'род', 'lineage',
        'духовность', 'spiritual', 'развитие', 'development',
        'одиночество', 'loneliness', 'изоляция', 'isolation',
        'власть', 'power', 'контроль', 'control',
        'самореализация', 'self_realization', 'призвание', 'vocation'
    ]
    
    def __init__(self, config: Optional[ContextSelectionConfig] = None):
        self.config = config or ContextSelectionConfig()
    
    def identify_karmic_themes(
        self,
        db: Session,
        user_id: int,
        user_profile: Optional[Dict[str, Any]] = None,
        current_query: Optional[str] = None,
        history_years: int = 3,
        vector_results_cache: Optional[List[Dict[str, Any]]] = None
    ) -> KarmaResult:
        """
        Идентификация кармических тем пользователя
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            user_profile: Профиль пользователя (натальные данные)
            current_query: Текущий запрос пользователя
            history_years: Количество лет истории для анализа
            
        Returns:
            KarmaResult с выявленными кармическими темами
        """
        start_time = datetime.now()
        
        if not self.config.KARMA_ENABLED:
            logger.info("Модуль кармических узлов отключен")
            return KarmaResult(
                themes=[],
                active_themes_count=0,
                processing_time_ms=0.0
            )
        
        # 1. Инициализация тем: загрузка базовых кармических тем из профиля
        base_themes = self._load_base_themes(db, user_id, user_profile)
        
        logger.info(f"Загружено {len(base_themes)} базовых кармических тем")
        
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
            logger.error(f"Ошибка запроса к БД в модуле кармы: {str(e)}", exc_info=True)
            return KarmaResult(
                themes=[],
                active_themes_count=0,
                processing_time_ms=0.0
            )
        
        logger.info(f"Анализ {len(entries)} событий для кармических тем")
        
        # 2. Семантический мониторинг: поиск событий, релевантных кармическим темам
        karmic_themes = []
        
        for theme in base_themes:
            # Поиск событий, релевантных теме
            try:
                relevant_events = self._find_relevant_events(
                    theme=theme,
                    entries=entries,
                    user_id=user_id,
                    current_query=current_query,
                    vector_results_cache=vector_results_cache
                )
            except Exception as e:
                logger.error(f"Ошибка поиска релевантных событий для темы {theme.get('name')}: {str(e)}", exc_info=True)
                relevant_events = []
            
            if not relevant_events:
                continue
            
            # 3. Подтверждение значимости: учет ручных маркеров и повторяемости
            manifestation_level = self._calculate_manifestation_level(
                theme=theme,
                events=relevant_events,
                entries=entries
            )
            
            # Проверяем минимальный уровень проявления
            if manifestation_level < 0.3:
                continue
            
            # 4. Формируем описание темы
            description = self._generate_theme_description(theme, relevant_events, manifestation_level)
            
            # Определяем источник темы
            source = 'natal_chart' if theme.get('from_natal_chart') else 'detected'
            
            # Преобразуем записи в SelectedEvent
            selected_events = []
            for entry in relevant_events[:10]:  # Берем первые 10 событий
                event = SelectedEvent(
                    id=entry.id,
                    text=format_event_text(entry),
                    date=entry.created_at,
                    significance_score=manifestation_level,
                    category=determine_event_category(entry),
                    tags=entry.tags if entry.tags else [],
                    source='karma_module'
                )
                selected_events.append(event)
            
            karmic_theme = KarmicTheme(
                theme=theme['name'],
                manifestation_level=manifestation_level,
                confirmed_events=selected_events,
                description=description,
                source=source
            )
            karmic_themes.append(karmic_theme)
        
        # Сортируем по уровню проявления
        karmic_themes.sort(key=lambda t: t.manifestation_level, reverse=True)
        
        # Лимитирование: выбор топ-N тем
        karmic_themes = karmic_themes[:self.config.KARMA_MAX_THEMES]
        
        # Вычисляем время обработки
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Выявлено {len(karmic_themes)} активных кармических тем за {processing_time_ms:.2f} мс")
        
        return KarmaResult(
            themes=karmic_themes,
            active_themes_count=len(karmic_themes),
            processing_time_ms=processing_time_ms
        )
    
    def _load_base_themes(
        self,
        db: Session,
        user_id: int,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Загрузка базовых кармических тем из профиля с кэшированием
        
        Использует кэш для избежания повторных запросов к БД
        """
        themes = []
        
        try:
            # Загружаем натальную карту пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"Пользователь {user_id} не найден")
                return themes
            
            # Пытаемся получить из кэша
            natal_chart = None
            chart_calculated_at = None
            
            if self.config.KARMA_CACHE_ENABLED:
                cached_data = natal_chart_cache.get(user_id)
                if cached_data:
                    natal_chart = cached_data.get('natal_chart')
                    chart_calculated_at = cached_data.get('calculated_at')
                    logger.debug(f"Натальная карта для пользователя {user_id} загружена из кэша")
            
            # Если нет в кэше, загружаем из БД
            if not natal_chart:
                try:
                    natal_chart = db.query(NatalChart).filter(
                        NatalChart.user_profile_id == user_id
                    ).order_by(desc(NatalChart.calculated_at)).first()
                    
                    if natal_chart:
                        chart_calculated_at = natal_chart.calculated_at
                        
                        # Сохраняем в кэш
                        if self.config.KARMA_CACHE_ENABLED:
                            natal_chart_cache.set(
                                user_id=user_id,
                                data={
                                    'natal_chart': natal_chart,
                                    'calculated_at': chart_calculated_at
                                },
                                chart_calculated_at=chart_calculated_at
                            )
                            logger.debug(f"Натальная карта для пользователя {user_id} сохранена в кэш")
                except Exception as e:
                    logger.error(f"Ошибка загрузки натальной карты для пользователя {user_id}: {str(e)}", exc_info=True)
                    natal_chart = None
            
            # Извлекаем кармические темы из натальной карты
            if natal_chart:
                try:
                    # Валидация данных натальной карты
                    if not self._validate_natal_chart(natal_chart):
                        logger.warning(f"Натальная карта для пользователя {user_id} содержит некорректные данные")
                        natal_chart = None
                    
                    if natal_chart:
                        # Анализируем планеты в 12 доме (карма)
                        planet_positions = natal_chart.planet_positions
                        if planet_positions:
                            for position in planet_positions:
                                if position.house == 12:
                                    # Планета в 12 доме указывает на кармическую тему
                                    theme_name = self._get_karmic_theme_from_planet(position.planet_name)
                                    if theme_name:
                                        # Получаем аспекты для этой планеты
                                        aspects = self._get_planet_aspects(natal_chart, position.planet_name)
                                        
                                        themes.append({
                                            'name': theme_name,
                                            'from_natal_chart': True,
                                            'planet': position.planet_name,
                                            'house': 12,
                                            'zodiac_sign': position.zodiac_sign,
                                            'is_retrograde': bool(position.is_retrograde),
                                            'aspects': aspects
                                        })
                    else:
                        logger.debug(f"Нет позиций планет в натальной карте для пользователя {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка извлечения кармических тем из натальной карты: {str(e)}", exc_info=True)
            
            # Добавляем темы из профиля пользователя (если есть)
            if user_profile:
                try:
                    profile_themes = user_profile.get('karmic_themes', [])
                    for theme_name in profile_themes:
                        themes.append({
                            'name': theme_name,
                            'from_natal_chart': False,
                            'source': 'user_profile'
                        })
                except Exception as e:
                    logger.error(f"Ошибка добавления тем из профиля: {str(e)}", exc_info=True)
            
            # Если нет тем из натальной карты, используем базовые темы
            if not themes:
                themes = [{'name': theme, 'from_natal_chart': False, 'source': 'default'}
                         for theme in self.KARMIC_THEMES[:5]]  # Берем первые 5 тем
                         
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке базовых тем для пользователя {user_id}: {str(e)}", exc_info=True)
            # Возвращаем базовые темы в случае ошибки
            themes = [{'name': theme, 'from_natal_chart': False, 'source': 'default'}
                     for theme in self.KARMIC_THEMES[:3]]
        
        return themes
    
    def _get_planet_aspects(self, natal_chart, planet_name: str) -> List[Dict[str, Any]]:
        """
        Получение аспектов для планеты из натальной карты
        
        Args:
            natal_chart: Объект NatalChart
            planet_name: Название планеты
            
        Returns:
            Список аспектов с информацией о типе и второй планете
        """
        aspects = []
        
        try:
            if not natal_chart or not natal_chart.aspects:
                return aspects
            
            # Ищем аспекты, где планета является участником
            for aspect in natal_chart.aspects:
                if aspect.planet_1_name.lower() == planet_name.lower():
                    aspects.append({
                        'type': aspect.aspect_type,
                        'planet_2': aspect.planet_2_name,
                        'is_major': aspect.aspect_type in ['conjunction', 'square', 'trine', 'opposition']
                    })
                elif aspect.planet_2_name.lower() == planet_name.lower():
                    aspects.append({
                        'type': aspect.aspect_type,
                        'planet_2': aspect.planet_1_name,
                        'is_major': aspect.aspect_type in ['conjunction', 'square', 'trine', 'opposition']
                    })
        except Exception as e:
            logger.error(f"Ошибка получения аспектов для планеты {planet_name}: {str(e)}", exc_info=True)
        
        return aspects
    
    def _get_karmic_theme_from_planet(self, planet_name: str) -> Optional[str]:
        """Получение кармической темы из планеты"""
        planet_themes = {
            'sun': 'самореализация',
            'moon': 'эмоции',
            'mercury': 'коммуникация',
            'venus': 'отношения',
            'mars': 'действие',
            'jupiter': 'расширение',
            'saturn': 'ограничения',
            'uranus': 'изменения',
            'neptune': 'иллюзии',
            'pluto': 'трансформация'
        }
        return planet_themes.get(planet_name.lower())
    
    def _find_relevant_events(
        self,
        theme: Dict[str, Any],
        entries: List[ContextEntry],
        user_id: int,
        current_query: Optional[str] = None,
        vector_results_cache: Optional[List[Dict[str, Any]]] = None
    ) -> List[ContextEntry]:
        """Поиск событий, релевантных кармической теме"""
        theme_name = theme['name']
        relevant_entries = []
        
        # Поиск по тегам и содержимому
        theme_keywords = [theme_name] + self._get_theme_keywords(theme_name)
        
        for entry in entries:
            # Проверяем теги
            if entry.tags:
                tags_lower = [tag.lower() for tag in entry.tags]
                if any(keyword.lower() in tags_lower for keyword in theme_keywords):
                    relevant_entries.append(entry)
                    continue
            
            # Проверяем содержимое
            content_lower = ""
            if entry.event_description:
                content_lower += entry.event_description.lower()
            if entry.user_message:
                content_lower += entry.user_message.lower()
            
            if any(keyword.lower() in content_lower for keyword in theme_keywords):
                relevant_entries.append(entry)
                continue
        
        # Дополнительный поиск через векторный поиск
        if current_query:
            # Используем кэш или выполняем новый поиск
            if vector_results_cache:
                # Фильтруем по порогу и добавляем тему в фильтрацию
                vector_results = [
                    r for r in vector_results_cache
                    if r.get('score', 0) >= self.config.KARMA_SIMILARITY_THRESHOLD
                ]
                logger.debug(f"Использован кэш векторных результатов для кармических тем: {len(vector_results)} записей")
            elif vector_service.client:
                try:
                    # Формируем запрос для векторного поиска
                    search_query = f"{current_query} {theme_name}"
                    
                    vector_results = vector_service.search_similar(
                        query_text=search_query,
                        user_id=user_id,
                        limit=20,
                        score_threshold=self.config.KARMA_SIMILARITY_THRESHOLD
                    )
                except Exception as e:
                    logger.error(f"Ошибка векторного поиска в модуле кармы: {str(e)}", exc_info=True)
                    vector_results = []
            else:
                vector_results = []
            
            # Получаем ID релевантных записей
            relevant_entry_ids = {
                result['payload'].get('entry_id')
                for result in vector_results
                if result['payload'].get('entry_id')
            }
            
            # Добавляем релевантные записи
            for entry in entries:
                if entry.id in relevant_entry_ids and entry not in relevant_entries:
                    relevant_entries.append(entry)
        
        return relevant_entries
    
    def _get_theme_keywords(self, theme_name: str) -> List[str]:
        """Получение ключевых слов для темы"""
        theme_keywords = {
            'отношения': ['партнерство', 'любовь', 'брак', 'relationship', 'partnership'],
            'работа': ['карьера', 'профессия', 'work', 'career', 'profession'],
            'здоровье': ['болезнь', 'лечение', 'health', 'illness', 'treatment'],
            'финансы': ['деньги', 'богатство', 'finance', 'money', 'wealth'],
            'семья': ['род', 'предки', 'family', 'lineage', 'ancestors'],
            'духовность': ['развитие', 'просветление', 'spiritual', 'development', 'enlightenment'],
            'самореализация': ['призвание', 'предназначение', 'self_realization', 'vocation', 'purpose']
        }
        return theme_keywords.get(theme_name.lower(), [])
    
    def _validate_natal_chart(self, natal_chart) -> bool:
        """
        Валидация данных натальной карты
        
        Проверяет корректность структуры данных для избежания сбоев.
        
        Args:
            natal_chart: Объект NatalChart
            
        Returns:
            True если данные валидны, False иначе
        """
        try:
            # Проверяем наличие обязательных полей
            if not hasattr(natal_chart, 'user_profile_id'):
                return False
            
            # Проверяем наличие связей (могут быть None, это нормально)
            # Но если они есть, проверяем структуру
            if hasattr(natal_chart, 'planet_positions') and natal_chart.planet_positions:
                for position in natal_chart.planet_positions:
                    if not hasattr(position, 'planet_name') or not hasattr(position, 'house'):
                        logger.warning("Некорректная структура planet_positions")
                        return False
            
            if hasattr(natal_chart, 'aspects') and natal_chart.aspects:
                for aspect in natal_chart.aspects:
                    if not hasattr(aspect, 'planet_1_name') or not hasattr(aspect, 'planet_2_name'):
                        logger.warning("Некорректная структура aspects")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации натальной карты: {str(e)}", exc_info=True)
            return False
    
    def _calculate_manifestation_level(
        self,
        theme: Dict[str, Any],
        events: List[ContextEntry],
        all_entries: List[ContextEntry]
    ) -> float:
        """
        Улучшенный расчет уровня проявления кармической темы
        
        ПРИМЕЧАНИЕ О ПРОИЗВОДИТЕЛЬНОСТИ:
        Расчет стал сложнее из-за учета астрологических аспектов.
        Для больших объемов данных рекомендуется:
        1. Кэшировать результаты расчета
        2. Предварительно рассчитывать уровни проявления и хранить в БД
        3. Использовать индексы для быстрого доступа к релевантным событиям
        
        Учитывает:
        - Частоту событий
        - Приоритет событий
        - Повторяемость
        - Астрологические аспекты (если тема из натальной карты)
        """
        if not events:
            return 0.0
        
        try:
            # 1. Базовая значимость на основе частоты
            frequency_score = min(1.0, len(events) / 10.0)  # Нормализуем к 1.0
            
            # 2. Значимость на основе приоритета событий
            priority_scores = []
            for entry in events:
                if entry.priority:
                    priority_scores.append(entry.priority / 5.0)  # Нормализуем к 1.0
            
            priority_score = (
                sum(priority_scores) / len(priority_scores) 
                if priority_scores else 0.5
            )
            
            # 3. Значимость на основе повторяемости
            repetition_score = 0.5
            if all_entries:
                event_ratio = len(events) / len(all_entries)
                repetition_score = min(1.0, event_ratio * 10)  # Нормализуем к 1.0
            
            # 4. Значимость на основе астрологических аспектов (если тема из натальной карты)
            aspect_score = 0.5  # По умолчанию нейтральная
            if theme.get('from_natal_chart') and theme.get('aspects'):
                aspects = theme['aspects']
                # Учитываем количество и тип аспектов
                major_aspects_count = sum(1 for a in aspects if a.get('is_major', False))
                total_aspects_count = len(aspects)
                
                if total_aspects_count > 0:
                    # Больше аспектов = выше значимость
                    aspect_ratio = major_aspects_count / total_aspects_count
                    aspect_score = 0.5 + (aspect_ratio * 0.5)  # От 0.5 до 1.0
                    
                    # Бонус за ретроградность планеты
                    if theme.get('is_retrograde'):
                        aspect_score = min(1.0, aspect_score + 0.1)
            
            # Комбинированная значимость с настраиваемыми весами
            scores = [
                frequency_score,
                priority_score,
                repetition_score,
                aspect_score
            ]
            
            weights = [
                self.config.KARMA_FREQUENCY_WEIGHT,
                self.config.KARMA_PRIORITY_WEIGHT,
                self.config.KARMA_REPETITION_WEIGHT,
                self.config.KARMA_ASPECT_WEIGHT
            ]
            
            manifestation_level = combine_scores(scores, weights)
            
            return max(0.0, min(1.0, manifestation_level))
            
        except Exception as e:
            logger.error(f"Ошибка расчета уровня проявления темы {theme.get('name')}: {str(e)}", exc_info=True)
            # Возвращаем базовую оценку на основе частоты
            return min(1.0, len(events) / 10.0) if events else 0.0
    
    def _generate_theme_description(
        self,
        theme: Dict[str, Any],
        events: List[ContextEntry],
        manifestation_level: float
    ) -> str:
        """Генерация описания кармической темы"""
        theme_name = theme['name']
        count = len(events)
        
        # Определяем уровень проявления
        if manifestation_level >= 0.7:
            level_text = "высокий"
        elif manifestation_level >= 0.4:
            level_text = "средний"
        else:
            level_text = "низкий"
        
        description = f"Кармическая тема '{theme_name}' проявляется с {level_text} уровнем интенсивности"
        description += f" (встречается {count} раз в истории)"
        
        # Добавляем источник темы и астрологическую информацию
        if theme.get('from_natal_chart'):
            planet = theme.get('planet', 'unknown')
            zodiac_sign = theme.get('zodiac_sign', '')
            aspects = theme.get('aspects', [])
            
            description += f". Тема определена из натальной карты (планета {planet} в 12 доме"
            if zodiac_sign:
                description += f", знак {zodiac_sign}"
            if theme.get('is_retrograde'):
                description += ", ретроградная"
            description += ")"
            
            if aspects:
                major_aspects = [a for a in aspects if a.get('is_major', False)]
                if major_aspects:
                    aspect_types = [a['type'] for a in major_aspects[:2]]  # Берем первые 2
                    description += f". Основные аспекты: {', '.join(aspect_types)}"
        
        return description
    

