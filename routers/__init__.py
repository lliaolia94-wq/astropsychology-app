from .astrology import router as astrology_router
from .contacts import router as contacts_router
from .ai import router as ai_router
from .context import router as context_router
from .general import router as general_router
from .users import router as users_router

__all__ = [
    "astrology_router",
    "contacts_router",
    "ai_router",
    "context_router",
    "general_router",
    "users_router",
]

