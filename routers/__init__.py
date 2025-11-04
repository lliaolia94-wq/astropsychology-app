from .astrology import router as astrology_router
from .contacts import router as contacts_router
from .ai import router as ai_router
from .context import router as context_router
from .general import router as general_router
from .users import router as users_router
from .auth import router as auth_router
from .natal_chart import router as natal_chart_router
from .geocoding import router as geocoding_router

try:
    from .guest import router as guest_router
except ImportError:
    guest_router = None

__all__ = [
    "astrology_router",
    "contacts_router",
    "ai_router",
    "context_router",
    "general_router",
    "users_router",
    "auth_router",
    "natal_chart_router",
    "geocoding_router",
    "guest_router",
]

