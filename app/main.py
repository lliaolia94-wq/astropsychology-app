from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импорты из наших модулей
from app.core.database import engine, Base
from app.api.v1.endpoints import (
    astrology_router,
    contacts_router,
    ai_router,
    context_router,
    general_router,
    users_router,
    auth_router,
    natal_chart_router
)
try:
    from app.api.v1.endpoints import geocoding_router
except ImportError:
    geocoding_router = None
try:
    from app.api.v1.endpoints import guest_router
except ImportError:
    guest_router = None

# Загружаем переменные окружения
load_dotenv()

tags_metadata = [
    {"name": "General", "description": "Базовые сервисные эндпоинты: корень и здоровье."},
    {"name": "Authentication", "description": "Аутентификация пользователей: регистрация, вход, восстановление пароля."},
    {"name": "Users", "description": "Управление пользователями и их профилями."},
    {"name": "Astrology", "description": "Расчёты натальных карт, транзитов и календарей."},
    {"name": "Contacts", "description": "Контакты пользователя для синастрий и упоминаний."},
    {"name": "AI", "description": "ИИ-астролог: шаблоны и чат."},
    {"name": "Context", "description": "Контекстные записи и извлечённые инсайты."},
    {"name": "Guest", "description": "Гостевые расчеты без регистрации."}
]

# FastAPI приложение
app = FastAPI(
    title="Astropsychology API",
    description="API для мобильного приложения Астопсихология",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Astropsychology Team",
        "email": "support@example.com"
    },
    license_info={
        "name": "Proprietary",
    }
)

# CORS (для удобной работы Swagger UI и внешних клиентов в DEV)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(general_router)
app.include_router(auth_router)
app.include_router(users_router)

    # подключаем роутеры модулей
app.include_router(astrology_router)
app.include_router(contacts_router)
app.include_router(ai_router)
app.include_router(context_router)
app.include_router(natal_chart_router)
if geocoding_router:
    app.include_router(geocoding_router)
if guest_router:
    app.include_router(guest_router)

# Статические файлы для веб-интерфейса
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Главная страница веб-интерфейса
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_root():
    """Главная страница веб-интерфейса"""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Astropsychology API работает! Веб-интерфейс не найден."}

# Service Worker для PWA (должен быть доступен с корня)
@app.get("/sw.js", response_class=FileResponse, include_in_schema=False)
async def service_worker():
    """Service Worker для PWA"""
    sw_path = os.path.join(os.path.dirname(__file__), "static", "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service Worker not found")

# Пересоздаем таблицы (удалит старые данные!)
def recreate_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы пересозданы")

# Раскомментируй следующую строку если нужно пересоздать таблицы
# recreate_tables()

# Или используй обычное создание если не хочешь терять данные
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Таблицы базы данных созданы/проверены")
except Exception as e:
    logger.error(f"❌ Ошибка при создании таблиц: {str(e)}", exc_info=True)

# Глобальный обработчик исключений для отладки
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Внутренняя ошибка сервера: {str(exc)}",
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=True
    )