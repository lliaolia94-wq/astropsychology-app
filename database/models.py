from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, DECIMAL, Date, Time
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.database import Base


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
    template_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


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
    event = Column(Text, nullable=True)
    emotion = Column(String(100), nullable=True)
    insight = Column(Text, nullable=True)
    astro_context = Column(Text, nullable=True)
    successful_strategy = Column(Text, nullable=True)
    tags = Column(JSON)
    is_important = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class SMSCode(Base):
    __tablename__ = "sms_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)  # Количество попыток ввода
    used = Column(Integer, default=0)  # 0 = не использован, 1 = использован