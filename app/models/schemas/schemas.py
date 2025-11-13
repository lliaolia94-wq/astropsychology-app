from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import validator, Field


# User Schemas
class UserCreate(BaseModel):
    """Обновление профиля пользователя (после регистрации)"""
    name: Optional[str] = None
    birth_date: Optional[str] = Field(None, description="Формат: YYYY-MM-DD")
    birth_time: Optional[str] = Field(None, description="Формат: HH:MM")
    birth_place: Optional[str] = Field(None, description="Старое поле для обратной совместимости")
    # Новые поля для расширенного профиля
    birth_location_name: Optional[str] = Field(None, description="Название города/места")
    birth_country: Optional[str] = Field(None, description="Страна")
    birth_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Широта от -90 до +90")
    birth_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Долгота от -180 до +180")
    timezone_name: Optional[str] = Field(None, description="Временная зона (например, Europe/Moscow)")
    birth_time_utc_offset: Optional[float] = Field(None, ge=-12, le=14, description="UTC offset в часах для ручной корректировки (например, +3.0, -4.0, +3.5)")
    # Поля для текущего местоположения
    current_location_name: Optional[str] = Field(None, description="Название текущего города/места")
    current_country: Optional[str] = Field(None, description="Текущая страна")
    current_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Текущая широта от -90 до +90")
    current_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Текущая долгота от -180 до +180")
    current_timezone_name: Optional[str] = Field(None, description="Временная зона текущего места")

    @validator('birth_latitude')
    def validate_latitude(cls, v):
        """Валидация широты"""
        if v is not None:
            if not (-90 <= v <= 90):
                raise ValueError('Широта должна быть в диапазоне от -90 до +90 градусов')
        return v

    @validator('birth_longitude')
    def validate_longitude(cls, v):
        """Валидация долготы"""
        if v is not None:
            if not (-180 <= v <= 180):
                raise ValueError('Долгота должна быть в диапазоне от -180 до +180 градусов')
        return v

    @validator('current_latitude')
    def validate_current_latitude(cls, v):
        """Валидация текущей широты"""
        if v is not None:
            if not (-90 <= v <= 90):
                raise ValueError('Текущая широта должна быть в диапазоне от -90 до +90 градусов')
        return v

    @validator('current_longitude')
    def validate_current_longitude(cls, v):
        """Валидация текущей долготы"""
        if v is not None:
            if not (-180 <= v <= 180):
                raise ValueError('Текущая долгота должна быть в диапазоне от -180 до +180 градусов')
        return v

    @validator('birth_time_utc_offset')
    def validate_utc_offset(cls, v):
        """Валидация UTC offset"""
        if v is not None:
            if not (-12 <= v <= 14):
                raise ValueError('UTC offset должен быть в диапазоне от -12 до +14 часов')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Сергеева Ольга",
                "birth_date": "1994-10-23",
                "birth_time": "19:30",
                "birth_place": "Семей, Казахстан",
                "birth_location_name": "Семей",
                "birth_country": "Казахстан",
                "birth_latitude": 50.4111,
                "birth_longitude": 80.2275,
                "timezone_name": "Asia/Almaty"
            }
        }


class UserResponse(BaseModel):
    id: int
    phone: str
    phone_verified: bool
    name: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    # Расширенные поля профиля
    birth_location_name: Optional[str] = None
    birth_country: Optional[str] = None
    birth_latitude: Optional[float] = None
    birth_longitude: Optional[float] = None
    timezone_name: Optional[str] = None
    # Поля для текущего местоположения
    current_location_name: Optional[str] = None
    current_country: Optional[str] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    current_timezone_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Contact Schemas
class ContactBase(BaseModel):
    name: str
    relationship_type: str
    custom_title: Optional[str] = None
    birth_date: str
    birth_time: str
    birth_place: str


class ContactCreate(ContactBase):
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Мария Иванова",
                "relationship_type": "друг",
                "custom_title": "Лучшая подруга",
                "birth_date": "1992-08-20",
                "birth_time": "09:15",
                "birth_place": "Санкт-Петербург, Россия"
            }
        }


class ContactResponse(ContactBase):
    id: int
    user_id: int
    aliases: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessageBase(BaseModel):
    content: str
    role: str  # user, assistant


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    template_type: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


# Обновленная версия с новыми полями
class ChatSessionResponseUpdated(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    parent_session_id: Optional[int] = None
    session_type: str = "regular"
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    template_type: Optional[str] = None
    mentioned_contacts: Optional[List[str]] = []  # алиасы упомянутых контактов

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Я чувствую напряжение на работе. Какие транзиты влияют?",
                "template_type": "transit_analysis",
                "mentioned_contacts": ["начальник"]
            }
        }


class ChatResponse(BaseModel):
    message_id: int
    session_id: int
    assistant_response: str
    timestamp: datetime


# Context Schemas
class ContextEntryBase(BaseModel):
    # Новые поля
    user_message: Optional[str] = None
    ai_response: Optional[str] = None
    emotional_state: Optional[str] = None
    event_description: Optional[str] = None
    insight_text: Optional[str] = None
    astro_context: Optional[Dict[str, Any]] = None
    successful_strategy: Optional[str] = None
    tags: Optional[List[str]] = []
    priority: int = 1  # 1-5
    entry_type: str = "auto"  # auto, manual, critical
    
    # Legacy поля (для обратной совместимости)
    event: Optional[str] = None
    emotion: Optional[str] = None
    insight: Optional[str] = None
    is_important: bool = False


class ContextEntryCreate(ContextEntryBase):
    session_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 1,
                "user_message": "Я чувствую напряжение на работе",
                "emotional_state": "тревога",
                "event_description": "Конфликт с начальником",
                "insight_text": "Нужно лучше коммуницировать",
                "tags": ["работа", "коммуникация"],
                "priority": 3,
                "entry_type": "manual"
            }
        }


class ContextEntryResponse(ContextEntryBase):
    id: int
    user_id: int
    session_id: int
    vector_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True




# Context API Schemas
class ContextSaveRequest(BaseModel):
    """Запрос на асинхронное сохранение контекста"""
    session_id: int
    user_message: str
    ai_response: str
    trigger_type: str = "message_count"  # message_count, timeout, manual, critical
    astro_context: Optional[Dict[str, Any]] = None


class ContextSaveResponse(BaseModel):
    """Ответ на запрос сохранения контекста"""
    task_id: str
    status: str = "queued"


class ContextRelevantRequest(BaseModel):
    """Запрос на получение релевантного контекста"""
    session_id: int
    current_message: str
    limit: int = 10


class ContextRelevantResponse(BaseModel):
    """Ответ с релевантным контекстом"""
    relevant_entries: List[Dict[str, Any]]
    search_time: Optional[float] = None


class ActiveSessionResponse(BaseModel):
    """Ответ с активной сессией"""
    session_id: int
    title: str
    created_at: datetime
    message_count: int
    session_type: str


# Template Schemas
class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    prompt_hint: str


# Authentication Schemas
class PhoneRequest(BaseModel):
    """Запрос на отправку SMS-кода"""
    phone: str
    country_code: Optional[str] = "+7"

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "9161234567",
                "country_code": "+7"
            }
        }


class SMSVerifyRequest(BaseModel):
    """Запрос на подтверждение SMS-кода"""
    phone: str
    code: str

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79161234567",
                "code": "123456"
            }
        }


class PasswordSetRequest(BaseModel):
    """Запрос на установку пароля"""
    phone: str
    password: str
    password_confirm: str

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79161234567",
                "password": "SecurePass123",
                "password_confirm": "SecurePass123"
            }
        }


class LoginRequest(BaseModel):
    """Запрос на вход"""
    phone: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79161234567",
                "password": "SecurePass123"
            }
        }


class TokenResponse(BaseModel):
    """Ответ с токенами"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление токена"""
    refresh_token: str


class MessageResponse(BaseModel):
    """Простой ответ с сообщением"""
    message: str


class UserAuthResponse(BaseModel):
    """Ответ с информацией о пользователе после аутентификации"""
    id: int
    phone: str
    phone_verified: bool
    name: Optional[str] = None

    class Config:
        from_attributes = True


# Natal Chart Schemas
class UserProfileUpdate(BaseModel):
    """Обновление профиля пользователя с данными для расчета натальной карты"""
    birth_date: Optional[str] = None  # Формат: "YYYY-MM-DD"
    birth_time: Optional[str] = None  # Формат: "HH:MM"
    birth_location_name: Optional[str] = None
    birth_country: Optional[str] = None
    birth_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Широта от -90 до +90")
    birth_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Долгота от -180 до +180")
    timezone_name: Optional[str] = None
    birth_time_utc_offset: Optional[float] = Field(None, ge=-12, le=14, description="UTC offset в часах для ручной корректировки (например, +3.0, -4.0, +3.5). Если указано, используется вместо автоматического определения по timezone_name")
    # Поля для текущего местоположения
    current_location_name: Optional[str] = Field(None, description="Название текущего города/места. Если указано, автоматически рассчитываются координаты и временная зона")
    current_country: Optional[str] = Field(None, description="Текущая страна")
    current_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Текущая широта от -90 до +90")
    current_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Текущая долгота от -180 до +180")
    current_timezone_name: Optional[str] = Field(None, description="Временная зона текущего места")

    @validator('birth_latitude')
    def validate_latitude(cls, v):
        """Валидация широты"""
        if v is not None:
            if not (-90 <= v <= 90):
                raise ValueError('Широта должна быть в диапазоне от -90 до +90 градусов')
        return v

    @validator('birth_longitude')
    def validate_longitude(cls, v):
        """Валидация долготы"""
        if v is not None:
            if not (-180 <= v <= 180):
                raise ValueError('Долгота должна быть в диапазоне от -180 до +180 градусов')
        return v

    @validator('birth_time_utc_offset')
    def validate_utc_offset(cls, v):
        """Валидация UTC offset"""
        if v is not None:
            if not (-12 <= v <= 14):
                raise ValueError('UTC offset должен быть в диапазоне от -12 до +14 часов')
        return v

    @validator('current_latitude')
    def validate_current_latitude(cls, v):
        """Валидация текущей широты"""
        if v is not None:
            if not (-90 <= v <= 90):
                raise ValueError('Текущая широта должна быть в диапазоне от -90 до +90 градусов')
        return v

    @validator('current_longitude')
    def validate_current_longitude(cls, v):
        """Валидация текущей долготы"""
        if v is not None:
            if not (-180 <= v <= 180):
                raise ValueError('Текущая долгота должна быть в диапазоне от -180 до +180 градусов')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "birth_date": "1990-05-15",
                "birth_time": "14:30",
                "birth_location_name": "Москва",
                "birth_country": "Россия",
                "birth_latitude": 55.7558,
                "birth_longitude": 37.6173,
                "timezone_name": "Europe/Moscow",
                "birth_time_utc_offset": 3.0,
                "current_location_name": "Санкт-Петербург",
                "current_country": "Россия"
            }
        }


class ManualCoordinatesRequest(BaseModel):
    """Запрос на ручной ввод координат"""
    birth_location_name: Optional[str] = None
    birth_country: Optional[str] = None
    birth_latitude: float = Field(..., ge=-90, le=90, description="Широта от -90 до +90")
    birth_longitude: float = Field(..., ge=-180, le=180, description="Долгота от -180 до +180")
    timezone_name: Optional[str] = None
    birth_time_utc_offset: Optional[float] = Field(None, ge=-12, le=14, description="UTC offset в часах для ручной корректировки (например, +3.0, -4.0, +3.5). Если указано, используется вместо автоматического определения по timezone_name")

    @validator('birth_latitude')
    def validate_latitude(cls, v):
        """Валидация широты"""
        if not (-90 <= v <= 90):
            raise ValueError('Широта должна быть в диапазоне от -90 до +90 градусов')
        return v

    @validator('birth_longitude')
    def validate_longitude(cls, v):
        """Валидация долготы"""
        if not (-180 <= v <= 180):
            raise ValueError('Долгота должна быть в диапазоне от -180 до +180 градусов')
        return v

    @validator('birth_time_utc_offset')
    def validate_utc_offset(cls, v):
        """Валидация UTC offset"""
        if v is not None:
            if not (-12 <= v <= 14):
                raise ValueError('UTC offset должен быть в диапазоне от -12 до +14 часов')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "birth_location_name": "Неизвестный город",
                "birth_country": "Россия",
                "birth_latitude": 55.7558,
                "birth_longitude": 37.6173,
                "timezone_name": "Europe/Moscow",
                "birth_time_utc_offset": 3.0
            }
        }


class GeocodingSearchRequest(BaseModel):
    """Запрос на поиск города"""
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    country: Optional[str] = None
    limit: Optional[int] = Field(10, ge=1, le=50, description="Максимальное количество результатов")


class GeocodingSearchResponse(BaseModel):
    """Ответ на поиск города"""
    cities: List[Dict[str, Any]]
    total: int


class GeocodingErrorResponse(BaseModel):
    """Ответ при ошибке геокодирования"""
    error: str
    error_code: str
    requires_manual_input: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Город не найден в базе данных",
                "error_code": "CITY_NOT_FOUND",
                "requires_manual_input": True,
                "message": "Не удалось найти координаты для указанного города. Пожалуйста, введите координаты вручную."
            }
        }


class PlanetPositionResponse(BaseModel):
    """Позиция планеты в натальной карте"""
    planet_name: str
    longitude: float
    zodiac_sign: str
    degree_in_sign: float = Field(..., description="Градусы внутри знака (0-29.99)")
    house: int
    is_retrograde: bool = False

    class Config:
        from_attributes = True


class AspectResponse(BaseModel):
    """Аспект между планетами"""
    planet_1_name: str
    planet_2_name: str
    aspect_type: str
    angle: float
    orb: float

    class Config:
        from_attributes = True


class HouseCuspidResponse(BaseModel):
    """Куспид дома"""
    house_number: int
    longitude: float
    zodiac_sign: str
    degree_in_sign: float = Field(..., description="Градусы внутри знака (0-29.99)")

    class Config:
        from_attributes = True


class AngleResponse(BaseModel):
    """Угол (ASC или MC)"""
    longitude: float
    zodiac_sign: str
    degree_in_sign: float = Field(..., description="Градусы внутри знака (0-29.99)")


class NatalChartResponse(BaseModel):
    """Полная натальная карта"""
    chart_id: int
    calculated_at: str
    houses_system: str
    zodiac_type: str
    planets: Dict[str, Any]  # Используем Any для гибкости
    aspects: List[AspectResponse]
    houses: Dict[str, Any]  # Используем Any для гибкости
    angles: Dict[str, AngleResponse]


class NatalChartCalculateRequest(BaseModel):
    """Запрос на расчет натальной карты"""
    houses_system: Optional[str] = "placidus"  # Система домов

    class Config:
        json_schema_extra = {
            "example": {
                "houses_system": "placidus"
            }
        }


class NatalChartCalculateResponse(BaseModel):
    """Ответ на запрос расчета натальной карты"""
    chart_id: int
    status: str
    message: str
    recalculated: bool


class NatalChartRecalculateRequest(BaseModel):
    """Запрос на пересчет натальной карты"""
    houses_system: Optional[str] = "placidus"

    class Config:
        json_schema_extra = {
            "example": {
                "houses_system": "placidus"
            }
        }


# ============ РЕГИСТРЫ КОНТЕКСТНОЙ ИНФОРМАЦИИ ============

class EventCreate(BaseModel):
    """Создание события"""
    event_type: str = Field(..., description="Тип события: user_message, ai_response, life_event, astrology_calculation")
    category: str = Field(..., description="Категория: career, health, relationships, finance, spiritual")
    event_date: datetime = Field(..., description="Дата события")
    effective_from: datetime = Field(..., description="Начало периода актуальности")
    effective_to: Optional[datetime] = Field(None, description="Конец периода актуальности (None = бессрочно)")
    title: Optional[str] = None
    description: Optional[str] = None
    user_message: Optional[str] = None
    ai_response: Optional[str] = None
    insight_text: Optional[str] = None
    emotional_state: Optional[str] = None
    emotional_intensity: Optional[float] = Field(None, ge=0, le=1)
    emotional_trigger: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(3, ge=1, le=5)
    session_id: Optional[int] = None
    contact_ids: Optional[List[int]] = None


class EventUpdate(BaseModel):
    """Обновление события"""
    title: Optional[str] = None
    description: Optional[str] = None
    emotional_state: Optional[str] = None
    emotional_intensity: Optional[float] = Field(None, ge=0, le=1)
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    effective_to: Optional[datetime] = None


class EventResponse(BaseModel):
    """Ответ с событием"""
    id: int
    user_id: int
    session_id: Optional[int] = None
    event_date: str
    created_at: str
    effective_from: str
    effective_to: Optional[str] = None
    event_type: str
    category: str
    priority: int
    title: Optional[str] = None
    description: Optional[str] = None
    user_message: Optional[str] = None
    ai_response: Optional[str] = None
    insight_text: Optional[str] = None
    emotional_state: Optional[str] = None
    emotional_intensity: Optional[float] = None
    emotional_trigger: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = None
    contact_ids: Optional[List[int]] = None


class ContactRegisterCreate(BaseModel):
    """Создание контакта в регистре"""
    name: str
    relationship_type: str = Field(..., description="family, friend, colleague, business, romantic")
    relationship_depth: Optional[int] = Field(None, ge=1, le=10)
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    timezone: Optional[str] = None
    interaction_frequency: Optional[str] = None
    tags: Optional[List[str]] = None
    privacy_level: Optional[str] = Field("private", description="public, private, hidden")


class ContactRegisterUpdate(BaseModel):
    """Обновление контакта"""
    name: Optional[str] = None
    relationship_type: Optional[str] = None
    relationship_depth: Optional[int] = Field(None, ge=1, le=10)
    interaction_frequency: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ContactRegisterResponse(BaseModel):
    """Ответ с контактом"""
    id: int
    user_id: int
    name: str
    relationship_type: str
    relationship_depth: Optional[int] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    timezone: Optional[str] = None
    interaction_frequency: Optional[str] = None
    last_interaction_date: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool
    privacy_level: str


class TransitCreate(BaseModel):
    """Создание транзита"""
    transit_type: str = Field(..., description="planet_transit, lunar_phase, eclipse, retrograde")
    planet_from: str
    planet_to: Optional[str] = None
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    transit_date: str = Field(..., description="YYYY-MM-DD")
    aspect_type: Optional[str] = None
    exact_time: Optional[datetime] = None
    orb: Optional[float] = None
    strength: Optional[float] = Field(None, ge=0, le=1)
    house: Optional[int] = Field(None, ge=1, le=12)
    interpretation: Optional[str] = None
    impact_level: str = Field(..., description="low, medium, high, critical")
    impact_areas: Optional[List[str]] = None


class TransitResponse(BaseModel):
    """Ответ с транзитом"""
    id: int
    user_id: int
    calculation_date: str
    start_date: str
    end_date: str
    transit_date: str
    transit_type: str
    planet_from: str
    planet_to: Optional[str] = None
    aspect_type: Optional[str] = None
    exact_time: Optional[str] = None
    orb: Optional[float] = None
    strength: Optional[float] = None
    house: Optional[int] = None
    interpretation: Optional[str] = None
    impact_level: str
    impact_areas: Optional[List[str]] = None


class ContextQueryRequest(BaseModel):
    """Запрос на получение контекстного среза"""
    days: Optional[int] = Field(None, description="Количество дней назад")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    categories: Optional[List[str]] = None
    emotional_states: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_priority: Optional[int] = Field(None, ge=1, le=5)
    max_priority: Optional[int] = Field(None, ge=1, le=5)
    include_contacts: bool = False
    include_transits: bool = False
    include_karmic_themes: bool = False
    limit: Optional[int] = Field(None, ge=1, le=1000)


class ContextSliceResponse(BaseModel):
    """Ответ с контекстным срезом"""
    events: List[EventResponse]
    contacts: Optional[List[ContactRegisterResponse]] = None
    transits: Optional[List[TransitResponse]] = None
    statistics: Dict[str, Any]
    patterns: List[Dict[str, Any]]