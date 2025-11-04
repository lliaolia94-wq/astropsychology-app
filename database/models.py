from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
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
    birth_date = Column(String(10), nullable=True)
    birth_time = Column(String(5), nullable=True)
    birth_place = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class NatalChart(Base):
    __tablename__ = "natal_charts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    sun_sign = Column(String(20))
    moon_sign = Column(String(20))
    ascendant_sign = Column(String(20))
    midheaven_sign = Column(String(20))
    planets_data = Column(Text)
    houses_data = Column(Text)
    angles_data = Column(Text)
    calculation_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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