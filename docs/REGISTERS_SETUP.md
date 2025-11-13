# Инструкция по настройке системы регистров

## Шаг 1: Применение миграции базы данных

Примените миграцию для создания таблиц регистров:

```bash
# Вариант 1: Через Alembic напрямую
alembic upgrade head

# Вариант 2: Через скрипт проекта
python scripts/run_migrations.py upgrade
```

Миграция `008_add_registers_tables.py` создаст следующие таблицы:
- `events_register` - регистр событий
- `contacts_register` - регистр контактов
- `transits_register` - регистр транзитов
- `virtual_slices` - виртуальные срезы
- `karmic_themes_register` - регистр кармических тем

## Шаг 2: Миграция существующих данных (опционально)

Если у вас есть данные в `context_entries`, их можно мигрировать в `events_register`:

```bash
# Проверка (dry-run) - без сохранения изменений
python scripts/migrate_context_to_events.py --dry-run

# Реальная миграция
python scripts/migrate_context_to_events.py

# Миграция для конкретного пользователя
python scripts/migrate_context_to_events.py --user-id 123

# Миграция с ограничением количества записей
python scripts/migrate_context_to_events.py --limit 100
```

## Шаг 3: Проверка работы API

После применения миграции API endpoints будут доступны по адресу:

- Swagger UI: `http://localhost:8000/docs`
- Endpoints регистров: `/api/v1/registers/*`

### Примеры использования API

#### Создание события

```bash
curl -X POST "http://localhost:8000/api/v1/registers/events?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_message",
    "category": "career",
    "event_date": "2025-01-15T10:00:00Z",
    "effective_from": "2025-01-15T10:00:00Z",
    "title": "Важное событие",
    "emotional_state": "anxiety",
    "priority": 4,
    "tags": ["работа", "конфликт"]
  }'
```

#### Создание контакта

```bash
curl -X POST "http://localhost:8000/api/v1/registers/contacts?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Иванов",
    "relationship_type": "colleague",
    "relationship_depth": 7,
    "birth_date": "1985-03-20",
    "birth_time": "12:00",
    "birth_place": "Москва",
    "tags": ["бизнес"]
  }'
```

#### Выполнение контекстного запроса

```bash
curl -X POST "http://localhost:8000/api/v1/registers/context/query?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "days": 30,
    "categories": ["career", "relationships"],
    "emotional_states": ["anxiety"],
    "include_contacts": true,
    "include_transits": true,
    "limit": 50
  }'
```

## Шаг 4: Запуск тестов

Запустите тесты для проверки работоспособности системы:

```bash
# Все тесты регистров
pytest tests/test_registers.py -v

# Конкретный тест
pytest tests/test_registers.py::TestEventsRegister::test_create_event -v

# С выводом подробной информации
pytest tests/test_registers.py -v -s
```

## Шаг 5: Интеграция с существующим кодом

### Использование в context_service

Система регистров может быть интегрирована с существующим `context_service`:

```python
from app.services.registers_service import registers_service
from app.services.context_query import ContextQuery

# При сохранении контекста создавать событие
event = registers_service.create_event(
    db=db,
    user_id=user_id,
    event_type='user_message',
    category='general',
    event_date=datetime.now(timezone.utc),
    effective_from=datetime.now(timezone.utc),
    user_message=user_message,
    ai_response=ai_response,
    emotional_state=emotional_state,
    tags=tags,
    priority=priority,
    session_id=session_id
)
```

### Использование контекстных запросов

```python
# Получение релевантного контекста через регистры
query = (ContextQuery(user_id=user_id, db=db)
    .for_days(30)
    .with_categories(['career', 'relationships'])
    .include_transits()
    .execute())

# Использование результатов
for event in query.events:
    print(f"Событие: {event['title']}")
```

## Проверка работоспособности

### 1. Проверка таблиц в БД

```python
from app.core.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

required_tables = [
    'events_register',
    'contacts_register',
    'transits_register',
    'virtual_slices',
    'karmic_themes_register'
]

for table in required_tables:
    assert table in tables, f"Таблица {table} не найдена!"
```

### 2. Проверка API endpoints

Откройте Swagger UI и проверьте наличие endpoints в разделе "Registers":
- POST `/api/v1/registers/events`
- GET `/api/v1/registers/events/{event_id}`
- POST `/api/v1/registers/contacts`
- POST `/api/v1/registers/transits`
- POST `/api/v1/registers/context/query`

## Устранение проблем

### Ошибка: "Таблица не найдена"

Убедитесь, что миграция применена:
```bash
alembic current
alembic upgrade head
```

### Ошибка: "Модуль не найден"

Убедитесь, что все зависимости установлены:
```bash
pip install -r requirements.txt
```

### Ошибка в тестах

Убедитесь, что используется тестовая БД:
```bash
# Проверьте DATABASE_URL в .env
# Для тестов должна быть отдельная БД
```

## Дополнительная информация

- Полная документация: `docs/README_REGISTERS.md`
- Примеры использования: см. `tests/test_registers.py`
- API документация: `http://localhost:8000/docs`

