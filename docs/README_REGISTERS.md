# Система регистров контекстной информации

## Обзор

Система регистров предоставляет масштабируемую архитектуру для хранения и обработки контекстной информации пользователя с поддержкой многомерного анализа данных по временным, тематическим и эмоциональным срезам.

## Архитектура

### Основные компоненты

1. **EventsRegister** - Основной регистр событий пользователя
2. **ContactsRegister** - Регистр контактов с астрологическими данными
3. **TransitsRegister** - Регистр транзитов
4. **VirtualSlices** - Регистр виртуальных срезов для кэширования
5. **KarmicThemesRegister** - Регистр кармических тем

## Использование

### Базовый пример

```python
from app.services.context_query import ContextQuery
from datetime import datetime, timedelta
from app.core.database import get_db

# Создание запроса
db = next(get_db())
query = (ContextQuery(user_id=123, db=db)
    .for_days(30)  # Последние 30 дней
    .with_categories(['career', 'relationships'])
    .with_emotional_state(['anxiety', 'frustration'])
    .include_transits()
    .include_contacts()
    .set_limit(50))

# Выполнение запроса
result = query.execute()

# Результат содержит:
# - result.events - список событий
# - result.contacts - список контактов
# - result.transits - список транзитов
# - result.statistics - статистика по срезу
# - result.patterns - выявленные паттерны
```

### Создание события

```python
from app.services.registers_service import registers_service
from datetime import datetime, timezone

event = registers_service.create_event(
    db=db,
    user_id=123,
    event_type='user_message',
    category='career',
    event_date=datetime.now(timezone.utc),
    effective_from=datetime.now(timezone.utc),
    effective_to=None,  # Бессрочно
    title='Важное событие',
    description='Описание события',
    user_message='Сообщение пользователя',
    emotional_state='anxiety',
    emotional_intensity=0.7,
    priority=4,
    tags=['работа', 'конфликт']
)
```

### Создание контакта

```python
contact = registers_service.create_contact(
    db=db,
    user_id=123,
    name='Иван Иванов',
    relationship_type='colleague',
    relationship_depth=7,
    birth_date=date(1990, 5, 15),
    birth_time=time(14, 30),
    birth_place='Москва',
    tags=['бизнес', 'поддерживающий']
)
```

### Создание транзита

```python
from datetime import date

transit = registers_service.create_transit(
    db=db,
    user_id=123,
    transit_type='planet_transit',
    planet_from='mars',
    planet_to='sun',
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 15),
    transit_date=date(2025, 1, 8),
    impact_level='high',
    aspect_type='square',
    interpretation='Марс в квадрате к Солнцу - период активности и конфликтов',
    impact_areas=['career', 'relationships']
)
```

## Параметры запросов

### Временные диапазоны

```python
# Последние N дней
query.for_days(30)

# Конкретный период
query.for_period(start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 31))
```

### Фильтрация

```python
# По категориям
query.with_categories(['career', 'health', 'relationships'])

# По эмоциональным состояниям
query.with_emotional_state(['anxiety', 'frustration', 'joy'])

# По тегам
query.with_tags(['работа', 'конфликт'])

# По приоритету
query.with_priority(min_priority=3, max_priority=5)
```

### Включение связанных данных

```python
# Включить контакты
query.include_contacts()

# Включить транзиты
query.include_transits()

# Включить кармические темы
query.include_karmic_themes()
```

## Миграция базы данных

Для применения миграций выполните:

```bash
alembic upgrade head
```

Миграция `008_add_registers_tables.py` создаст все необходимые таблицы и индексы.

## Интеграция с существующим кодом

### Миграция из ContextEntry в EventsRegister

Существующие записи `ContextEntry` можно мигрировать в `EventsRegister`:

```python
from app.models.database.models import ContextEntry, EventsRegister
from datetime import datetime, timezone

# Пример миграции одной записи
def migrate_context_entry_to_event(db, context_entry: ContextEntry):
    event = EventsRegister(
        user_id=context_entry.user_id,
        session_id=context_entry.session_id,
        event_type='user_message',
        category='general',  # Определить по контексту
        event_date=context_entry.created_at or datetime.now(timezone.utc),
        effective_from=context_entry.created_at or datetime.now(timezone.utc),
        effective_to=None,
        user_message=context_entry.user_message,
        ai_response=context_entry.ai_response,
        emotional_state=context_entry.emotional_state,
        insight_text=context_entry.insight_text,
        tags=context_entry.tags,
        priority=context_entry.priority,
        astrological_context=context_entry.astro_context
    )
    db.add(event)
    db.commit()
```

## Производительность

### Индексы

Система автоматически создает индексы для оптимизации запросов:

- `idx_events_user_date` - для временных запросов
- `idx_events_type_category` - для фильтрации по типу и категории
- `idx_events_emotional` - для эмоциональных паттернов
- `idx_transits_user_period` - для запросов транзитов по периоду
- И другие...

### Кэширование

Используйте `VirtualSlices` для кэширования часто используемых запросов:

```python
# Создание виртуального среза
slice = VirtualSlices(
    user_id=123,
    slice_name='monthly_career_events',
    slice_type='temporal',
    date_from=datetime(2025, 1, 1),
    date_to=datetime(2025, 1, 31),
    filters={'categories': ['career']},
    is_cached=True,
    cache_ttl_hours=24
)
```

## Расширение функциональности

### Добавление новых типов событий

```python
# В EventsRegister.event_type можно использовать:
# - 'user_message'
# - 'ai_response'
# - 'life_event'
# - 'astrology_calculation'
# - 'custom_type'  # Ваш тип
```

### Добавление новых категорий

```python
# В EventsRegister.category можно использовать:
# - 'career'
# - 'health'
# - 'relationships'
# - 'finance'
# - 'spiritual'
# - 'custom_category'  # Ваша категория
```

## Примеры использования

### Анализ эмоциональных паттернов

```python
query = (ContextQuery(user_id=123, db=db)
    .for_days(90)
    .with_emotional_state(['anxiety', 'stress'])
    .execute())

# Анализ паттернов
for pattern in result.patterns:
    print(f"Паттерн: {pattern['description']}")
    print(f"Частота: {pattern['frequency']}")
```

### Поиск событий с транзитами

```python
query = (ContextQuery(user_id=123, db=db)
    .for_period(start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 31))
    .include_transits()
    .with_categories(['career'])
    .execute())

# Связь событий с транзитами
for event in result.events:
    event_date = datetime.fromisoformat(event['event_date']).date()
    related_transits = [t for t in result.transits 
                       if t['start_date'] <= event_date <= t['end_date']]
    print(f"Событие {event['title']} связано с транзитами: {len(related_transits)}")
```

## Дополнительная информация

- См. техническое задание в `docs/` для полной спецификации
- API endpoints будут добавлены в следующих версиях
- Мониторинг и аналитика - в разработке

