"""API v1 Endpoints"""
from .auth import router as auth_router
from .users import router as users_router
from .astrology import router as astrology_router
from .contacts import router as contacts_router
from .ai import router as ai_router
from .context import router as context_router
from .natal_chart import router as natal_chart_router
from .general import router as general_router

try:
    from .geocoding import router as geocoding_router
except ImportError:
    geocoding_router = None

try:
    from .guest import router as guest_router
except ImportError:
    guest_router = None

__all__ = [
    "auth_router",
    "users_router",
    "astrology_router",
    "contacts_router",
    "ai_router",
    "context_router",
    "natal_chart_router",
    "geocoding_router",
    "guest_router",
    "general_router",
]
