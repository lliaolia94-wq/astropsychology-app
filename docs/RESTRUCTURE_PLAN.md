# План реорганизации структуры проекта

## Текущая структура (проблемы)

- Много файлов в корне проекта (main.py, config.py, run_*.py, apply_*.py, check_*.py)
- Смешение скриптов, конфигурации и основного кода
- Неясное разделение между рабочими скриптами и утилитами

## Новая структура (предложение)

```
astropsychology-app/
├── app/                          # Основное приложение
│   ├── __init__.py
│   ├── main.py                   # Точка входа приложения
│   │
│   ├── api/                      # API слой
│   │   ├── __init__.py
│   │   └── v1/                   # Версия API v1
│   │       ├── __init__.py
│   │       └── endpoints/        # Эндпоинты (роутеры)
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── astrology.py
│   │           ├── contacts.py
│   │           ├── ai.py
│   │           ├── context.py
│   │           ├── natal_chart.py
│   │           ├── geocoding.py
│   │           ├── guest.py
│   │           └── general.py
│   │
│   ├── core/                     # Ядро приложения
│   │   ├── __init__.py
│   │   ├── config.py             # Конфигурация
│   │   ├── database.py           # Подключение к БД
│   │   ├── security.py           # Безопасность (JWT и т.д.)
│   │   └── dependencies.py       # FastAPI зависимости
│   │
│   ├── models/                   # Модели данных
│   │   ├── __init__.py
│   │   ├── database/             # SQLAlchemy модели
│   │   │   ├── __init__.py
│   │   │   └── models.py
│   │   └── schemas/              # Pydantic схемы
│   │       ├── __init__.py
│   │       └── schemas.py
│   │
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── astro_service.py
│   │   ├── ai_service.py
│   │   ├── cache_service.py
│   │   ├── context_service.py
│   │   ├── geocoding_service.py
│   │   ├── natal_chart_service.py
│   │   ├── phone_validator.py
│   │   ├── rate_limiter.py
│   │   ├── redis_service.py
│   │   ├── sms_service.py
│   │   ├── sqlite_queue_service.py
│   │   ├── synastry_service.py
│   │   └── vector_service.py
│   │
│   └── workers/                  # Фоновые задачи
│       ├── __init__.py
│       ├── context_worker.py
│       └── run_context_worker.py
│
├── alembic/                      # Миграции БД (остается)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── scripts/                      # Утилиты и скрипты
│   ├── __init__.py
│   ├── check_dependencies.py
│   ├── check_migrations.py
│   ├── convert_geonames.py
│   ├── download_cities.py
│   ├── install_pyswisseph.py
│   ├── load_cities_db.py
│   └── run_migrations.py
│
├── tests/                        # Тесты (остается)
│   ├── __init__.py
│   ├── conftest.py
│   └── ...
│
├── static/                       # Статические файлы (остается)
│   ├── index.html
│   ├── app.js
│   └── ...
│
├── data/                         # Данные (остается)
│   ├── cities_db.json
│   └── cities.csv
│
├── docs/                         # Документация
│   ├── README.md
│   ├── INSTALL_WINDOWS.md
│   ├── QUICKSTART.md
│   ├── README_*.md
│   └── RESTRUCTURE_PLAN.md
│
├── .env.example                  # Пример переменных окружения
├── .gitignore                    # Git ignore
├── alembic.ini                   # Конфигурация Alembic
├── pytest.ini                    # Конфигурация pytest
├── requirements.txt              # Зависимости Python
├── README.md                     # Главный README
│
└── run.py                        # Скрипт запуска приложения
```

## Шаги миграции

1. Создать новую структуру папок
2. Переместить файлы
3. Обновить импорты во всех файлах
4. Обновить пути в конфигурационных файлах
5. Протестировать запуск приложения

## Преимущества новой структуры

✅ **Четкое разделение** - API, core, models, services, workers
✅ **Масштабируемость** - легко добавлять новые версии API (v2, v3)
✅ **Чистота** - корневая папка содержит только важные файлы
✅ **Стандартность** - следует best practices FastAPI проектов
✅ **Читаемость** - понятно, где что находится

