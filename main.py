from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Импорты из наших модулей
from database.database import engine, Base
from routers import astrology_router, contacts_router, ai_router, context_router, general_router, users_router

# Загружаем переменные окружения
load_dotenv()

tags_metadata = [
    {"name": "General", "description": "Базовые сервисные эндпоинты: корень и здоровье."},
    {"name": "Users", "description": "Управление пользователями и их профилями."},
    {"name": "Astrology", "description": "Расчёты натальных карт, транзитов и календарей."},
    {"name": "Contacts", "description": "Контакты пользователя для синастрий и упоминаний."},
    {"name": "AI", "description": "ИИ-астролог: шаблоны и чат."},
    {"name": "Context", "description": "Контекстные записи и извлечённые инсайты."}
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
app.include_router(users_router)

    # подключаем роутеры модулей
app.include_router(astrology_router)
app.include_router(contacts_router)
app.include_router(ai_router)
app.include_router(context_router)

# Пересоздаем таблицы (удалит старые данные!)
def recreate_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы пересозданы")

# Раскомментируй следующую строку если нужно пересоздать таблицы
# recreate_tables()

# Или используй обычное создание если не хочешь терять данные
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=True
    )