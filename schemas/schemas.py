from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


# User Schemas
class UserCreate(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_place: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Тестовый Пользователь",
                "birth_date": "1990-05-15",
                "birth_time": "14:30",
                "birth_place": "Москва, Россия"
            }
        }


class UserResponse(BaseModel):
    id: int
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
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
    event: Optional[str] = None
    emotion: Optional[str] = None
    insight: Optional[str] = None
    astro_context: Optional[str] = None
    successful_strategy: Optional[str] = None
    tags: Optional[List[str]] = []
    is_important: bool = False


class ContextEntryCreate(ContextEntryBase):
    class Config:
        json_schema_extra = {
            "example": {
                "event": "Успешно провела презентацию проекта",
                "emotion": "радость",
                "insight": "Лучше всего работаю утром",
                "astro_context": "Меркурий в трине с Юпитером",
                "successful_strategy": "Глубокая подготовка + медитация",
                "tags": ["работа", "успех", "коммуникация"],
                "is_important": True
            }
        }


class ContextEntryResponse(ContextEntryBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Template Schemas
class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    prompt_hint: str