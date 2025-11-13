from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, DECIMAL, Date, Time, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
import os

# JSONB для PostgreSQL, JSON для SQLite
try:
    from sqlalchemy.dialects.postgresql import JSONB
    USE_JSONB = os.getenv("DATABASE_URL", "").startswith("postgresql")
except ImportError:
    USE_JSONB = False


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone_verified = Column(Integer, default=0)  # 0 = не подтвержден, 1 = подтвержден
    name = Column(String(100), nullable=True)
    birth_date = Column(String(10), nullable=True)  # Для обратной совместимости
    birth_time = Column(String(5), nullable=True)  # Для обратной совместимости
    birth_place = Column(String(200), nullable=True)  # Для обратной совместимости
    
    # Новые поля для расширенного профиля
    birth_date_detailed = Column(Date, nullable=True)  # Дата рождения
    birth_time_detailed = Column(Time, nullable=True)  # Время рождения (локальное время места рождения)
    birth_time_utc = Column(DateTime, nullable=True)  # Рассчитанное время в UTC
    birth_location_name = Column(String(200), nullable=True)  # Название города/места
    birth_country = Column(String(100), nullable=True)  # Страна
    birth_latitude = Column(DECIMAL(9, 6), nullable=True)  # Географическая широта
    birth_longitude = Column(DECIMAL(9, 6), nullable=True)  # Географическая долгота
    timezone_name = Column(String(100), nullable=True)  # Название временной зоны (например, "Europe/Moscow")
    birth_time_utc_offset = Column(DECIMAL(5, 2), nullable=True)  # UTC offset в часах для ручной корректировки (например, +3.0, -4.0, +3.5)
    
    # Поля для текущего местоположения пользователя (для расчета транзитов)
    current_location_name = Column(String(200), nullable=True)  # Название текущего города/места
    current_country = Column(String(100), nullable=True)  # Текущая страна
    current_latitude = Column(DECIMAL(9, 6), nullable=True)  # Текущая географическая широта
    current_longitude = Column(DECIMAL(9, 6), nullable=True)  # Текущая географическая долгота
    current_timezone_name = Column(String(100), nullable=True)  # Название временной зоны текущего места
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Связь с натальными картами
    natal_charts = relationship("NatalChart", back_populates="user_profile", cascade="all, delete-orphan")


class NatalChart(Base):
    __tablename__ = "natal_charts_natalchart"

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    houses_system = Column(String(20), default='placidus', nullable=False)  # Система домов
    zodiac_type = Column(String(10), default='tropical', nullable=False)  # Тип зодиака
    
    # Связи
    user_profile = relationship("User", back_populates="natal_charts")
    planet_positions = relationship("PlanetPosition", back_populates="natal_chart", cascade="all, delete-orphan")
    aspects = relationship("Aspect", back_populates="natal_chart", cascade="all, delete-orphan")
    house_cuspids = relationship("HouseCuspid", back_populates="natal_chart", cascade="all, delete-orphan")


class PlanetPosition(Base):
    __tablename__ = "natal_charts_planetposition"

    id = Column(Integer, primary_key=True, index=True)
    natal_chart_id = Column(Integer, ForeignKey("natal_charts_natalchart.id"), nullable=False)
    planet_name = Column(String(20), nullable=False)  # 'sun', 'moon', 'mercury', etc.
    longitude = Column(DECIMAL(10, 6), nullable=False)  # Эклиптическая долгота в градусах (0° - 360°)
    zodiac_sign = Column(String(20), nullable=False)  # 'aries', 'taurus', etc. (увеличено для 'sagittarius')
    house = Column(Integer, nullable=False)  # Номер дома, в котором находится планета (1-12)
    is_retrograde = Column(Integer, default=0, nullable=False)  # 0 = директная, 1 = ретроградная
    
    natal_chart = relationship("NatalChart", back_populates="planet_positions")


class Aspect(Base):
    __tablename__ = "natal_charts_aspect"

    id = Column(Integer, primary_key=True, index=True)
    natal_chart_id = Column(Integer, ForeignKey("natal_charts_natalchart.id"), nullable=False)
    planet_1_name = Column(String(20), nullable=False)  # Первая планета в аспекте
    planet_2_name = Column(String(20), nullable=False)  # Вторая планета в аспекте
    aspect_type = Column(String(20), nullable=False)  # 'conjunction', 'sextile', 'square', 'trine', 'opposition'
    angle = Column(DECIMAL(5, 2), nullable=False)  # Точный угол между планетами
    orb = Column(DECIMAL(4, 2), nullable=False)  # Орбис аспекта (насколько он неточен)
    
    natal_chart = relationship("NatalChart", back_populates="aspects")


class HouseCuspid(Base):
    __tablename__ = "natal_charts_housecuspid"

    id = Column(Integer, primary_key=True, index=True)
    natal_chart_id = Column(Integer, ForeignKey("natal_charts_natalchart.id"), nullable=False)
    house_number = Column(Integer, nullable=False)  # Номер дома (1-12)
    longitude = Column(DECIMAL(10, 6), nullable=False)  # Эклиптическая долгота куспида дома в градусах
    zodiac_sign = Column(String(20), nullable=False)  # Знак зодиака на куспиде дома (увеличено для 'sagittarius')
    
    natal_chart = relationship("NatalChart", back_populates="house_cuspids")


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = {'extend_existing': True}  # ← Добавьте эту строку

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    custom_title = Column(String(100), nullable=True)
    birth_date = Column(String(10), nullable=False)
    birth_time = Column(String(5), nullable=False)
    birth_place = Column(String(200), nullable=False)
    aliases = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    template_type = Column(String(50), nullable=True)  # Оставляем для обратной совместимости
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Integer, default=1)  # 1 = активна, 0 = неактивна
    parent_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    session_type = Column(String(50), default='regular')  # regular, emergency, decision

    user = relationship("User")
    parent_session = relationship("ChatSession", remote_side=[id], backref="child_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    context_entries = relationship("ContextEntry", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")


class ContextEntry(Base):
    __tablename__ = "context_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    user_message = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    emotional_state = Column(String(100), nullable=True)  # Переименовано из emotion
    event_description = Column(Text, nullable=True)  # Переименовано из event
    insight_text = Column(Text, nullable=True)  # Переименовано из insight
    astro_context = Column(JSONB if USE_JSONB else JSON, nullable=True)  # JSONB для PostgreSQL, JSON для SQLite
    successful_strategy = Column(Text, nullable=True)
    tags = Column(JSON)  # TEXT[] в PostgreSQL будет через JSON
    priority = Column(Integer, default=1)  # 1-5, где 5 - максимальная важность
    entry_type = Column(String(20), default='auto')  # auto, manual, critical
    vector_id = Column(String(36), nullable=True)  # UUID вектора в Qdrant
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Обратная совместимость (legacy поля)
    event = Column(Text, nullable=True)  # Deprecated, используйте event_description
    emotion = Column(String(100), nullable=True)  # Deprecated, используйте emotional_state
    insight = Column(Text, nullable=True)  # Deprecated, используйте insight_text
    is_important = Column(Integer, default=0)  # Deprecated, используйте priority

    user = relationship("User")
    session = relationship("ChatSession", back_populates="context_entries")


class SMSCode(Base):
    __tablename__ = "sms_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)  # Количество попыток ввода
    used = Column(Integer, default=0)  # 0 = не использован, 1 = использован


# ============ РЕГИСТРЫ КОНТЕКСТНОЙ ИНФОРМАЦИИ ============

class EventsRegister(Base):
    """
    Основной регистр событий пользователя
    Централизованное хранение всех значимых событий с временными метками, классификацией и контекстом
    """
    __tablename__ = "events_register"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)  # для группировки событий одной сессии
    
    # Временные метки
    event_date = Column(DateTime, nullable=False, index=True)  # дата события
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    effective_from = Column(DateTime, nullable=False)  # начало периода актуальности
    effective_to = Column(DateTime, nullable=True)  # конец периода актуальности (NULL = бессрочно)
    
    # Классификация
    event_type = Column(String(50), nullable=False, index=True)  # 'user_message', 'ai_response', 'life_event', 'astrology_calculation'
    category = Column(String(50), nullable=False, index=True)  # career, health, relationships, finance, spiritual
    priority = Column(Integer, default=3)  # 1-5, где 5 - максимальная важность
    
    # Содержимое
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    user_message = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    insight_text = Column(Text, nullable=True)
    
    # Эмоциональный контекст
    emotional_state = Column(String(50), nullable=True, index=True)  # состояние эмоций
    emotional_intensity = Column(DECIMAL(3, 2), nullable=True)  # интенсивность 0-1
    emotional_trigger = Column(String(200), nullable=True)  # триггер эмоции
    
    # Астрологический контекст
    astrological_context = Column(JSONB if USE_JSONB else JSON, nullable=True)  # транзиты, аспекты на момент события
    natal_chart_snapshot_id = Column(Integer, ForeignKey("natal_charts_natalchart.id"), nullable=True)  # снимок натальной карты
    
    # Метаданные
    tags = Column(JSON, nullable=True)  # массив тегов ['работа', 'конфликт', 'решение']
    source = Column(String(100), nullable=True)  # 'user_input', 'system_generated', 'astrology_calc'
    confidence_score = Column(DECIMAL(3, 2), default=1.0)  # оценка достоверности 0-1
    
    # Ссылки на связанные сущности
    contact_ids = Column(JSON, nullable=True)  # массив ID контактов
    location_id = Column(Integer, nullable=True)  # ID локации (для будущего расширения)
    business_context_id = Column(Integer, nullable=True)  # ID бизнес-контекста (для будущего расширения)
    
    # Relationships
    user = relationship("User")
    session = relationship("ChatSession")
    natal_chart_snapshot = relationship("NatalChart")
    
    # Индексы создаются через миграцию


class ContactsRegister(Base):
    """
    Регистр контактов пользователя
    Хранение информации о значимых людях с расчетными астрологическими данными и динамикой отношений
    """
    __tablename__ = "contacts_register"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Основная информация
    name = Column(String(200), nullable=False)
    relationship_type = Column(String(50), nullable=False, index=True)  # family, friend, colleague, business, romantic
    relationship_depth = Column(Integer, nullable=True)  # 1-10, где 1=поверхностный, 10=глубокий
    
    # Астрологические данные
    birth_date = Column(Date, nullable=True)
    birth_time = Column(Time, nullable=True)
    birth_place = Column(String(300), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Рассчитанные данные
    natal_chart_data = Column(JSONB if USE_JSONB else JSON, nullable=True)  # данные натальной карты контакта
    synastry_with_user = Column(JSONB if USE_JSONB else JSON, nullable=True)  # синастрия с пользователем
    composite_chart = Column(JSONB if USE_JSONB else JSON, nullable=True)  # композитная карта
    
    # Динамика отношений
    interaction_frequency = Column(String(20), nullable=True)  # 'daily', 'weekly', 'monthly', 'rarely'
    last_interaction_date = Column(DateTime, nullable=True)
    emotional_pattern = Column(JSONB if USE_JSONB else JSON, nullable=True)  # паттерны эмоционального взаимодействия
    
    # Метаданные
    tags = Column(JSON, nullable=True)  # массив тегов ['бизнес', 'конфликтный', 'поддерживающий']
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    privacy_level = Column(String(20), default='private', nullable=False)  # 'public', 'private', 'hidden'
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User")


class TransitsRegister(Base):
    """
    Регистр транзитов
    Хранение предварительно рассчитанных астрологических транзитов с периодами действия и интерпретациями
    """
    __tablename__ = "transits_register"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Период действия
    calculation_date = Column(Date, nullable=False)  # дата расчета
    start_date = Column(Date, nullable=False, index=True)  # начало периода транзита
    end_date = Column(Date, nullable=False, index=True)  # конец периода транзита
    transit_date = Column(Date, nullable=False, index=True)  # конкретная дата транзита (для индексации)
    
    # Астрологические данные
    transit_type = Column(String(50), nullable=False, index=True)  # 'planet_transit', 'lunar_phase', 'eclipse', 'retrograde'
    planet_from = Column(String(20), nullable=False, index=True)  # транзитирующая планета
    planet_to = Column(String(20), nullable=True, index=True)  # планета/точка в натальной карте
    aspect_type = Column(String(20), nullable=True)  # 'conjunction', 'square', 'trine'
    exact_time = Column(DateTime, nullable=True)  # точное время аспекта
    
    # Астрологические параметры
    orb = Column(DECIMAL(4, 2), nullable=True)  # орбис
    strength = Column(DECIMAL(3, 2), nullable=True)  # сила аспекта 0-1
    house = Column(Integer, nullable=True)  # дом в натальной карте (1-12)
    
    # Интерпретация
    interpretation = Column(Text, nullable=True)  # текст интерпретации
    impact_level = Column(String(20), nullable=False, index=True)  # 'low', 'medium', 'high', 'critical'
    impact_areas = Column(JSON, nullable=True)  # области влияния: ['career', 'health', 'relationships']
    
    # Связи
    related_transit_ids = Column(JSON, nullable=True)  # связанные транзиты
    triggered_event_ids = Column(JSON, nullable=True)  # события, вызванные этим транзитом
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User")


class VirtualSlices(Base):
    """
    Регистр виртуальных срезов
    Кэширование часто используемых запросов для ускорения работы системы
    """
    __tablename__ = "virtual_slices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    slice_name = Column(String(100), nullable=False)
    
    # Параметры среза
    slice_type = Column(String(50), nullable=False, index=True)  # 'temporal', 'thematic', 'emotional', 'astrological'
    date_from = Column(DateTime, nullable=True, index=True)
    date_to = Column(DateTime, nullable=True, index=True)
    filters = Column(JSONB if USE_JSONB else JSON, nullable=False)  # условия фильтрации в JSON
    
    # Результаты среза (кэш)
    included_event_ids = Column(JSON, nullable=True)  # массив ID событий
    included_contact_ids = Column(JSON, nullable=True)  # массив ID контактов
    included_transit_ids = Column(JSON, nullable=True)  # массив ID транзитов
    
    # Статистика среза
    events_count = Column(Integer, default=0, nullable=False)
    patterns_detected = Column(JSONB if USE_JSONB else JSON, nullable=True)  # выявленные паттерны
    summary_statistics = Column(JSONB if USE_JSONB else JSON, nullable=True)  # статистика по срезу
    
    # Метаданные
    is_cached = Column(Boolean, default=False, nullable=False)
    cache_ttl_hours = Column(Integer, default=24, nullable=False)
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User")


class KarmicThemesRegister(Base):
    """
    Регистр кармических тем
    Выявление и отслеживание сквозных кармических паттернов пользователя
    """
    __tablename__ = "karmic_themes_register"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Идентификация темы
    theme_name = Column(String(100), nullable=False)
    theme_type = Column(String(50), nullable=False, index=True)  # 'natal', 'transits', 'life_events', 'relationships'
    description = Column(Text, nullable=True)
    
    # Астрологические индикаторы
    natal_indicators = Column(JSONB if USE_JSONB else JSON, nullable=True)  # планеты в 12 доме, узлы и т.д.
    transit_indicators = Column(JSONB if USE_JSONB else JSON, nullable=True)  # транзиты, активирующие тему
    
    # Проявление в жизни
    manifestation_level = Column(DECIMAL(3, 2), nullable=True)  # уровень проявления 0-1
    first_manifested_date = Column(DateTime, nullable=True)
    last_manifested_date = Column(DateTime, nullable=True)
    manifestation_count = Column(Integer, default=0, nullable=False)
    
    # Связанные события и контакты
    related_event_ids = Column(JSON, nullable=True)  # массив ID событий
    related_contact_ids = Column(JSON, nullable=True)  # массив ID контактов
    triggering_transit_ids = Column(JSON, nullable=True)  # массив ID транзитов
    
    # Статус и приоритет
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    resolution_status = Column(String(20), default='unresolved', nullable=False, index=True)  # 'unresolved', 'in_progress', 'resolved'
    priority = Column(Integer, nullable=True)  # 1-5
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User")