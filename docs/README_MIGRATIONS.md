# Миграции базы данных

## Проверка полей

### ✅ Поля в моделях

Все необходимые поля присутствуют в моделях:

#### 1. User модель
- ✅ `birth_time_utc` - DateTime, nullable=True

#### 2. NatalChart модель
- ✅ `houses_system` - String(20), default='placidus', nullable=False
- ✅ `zodiac_type` - String(10), default='tropical', nullable=False

#### 3. PlanetPosition модель
- ✅ `is_retrograde` - Integer, default=0, nullable=False

## Использование миграций

### Вариант 1: Alembic (рекомендуется)

```bash
# Установка
pip install alembic

# Применение миграций
alembic upgrade head

# Проверка текущей версии
alembic current

# Откат миграции
alembic downgrade -1
```

### Вариант 2: Скрипт миграции

```bash
# Применение миграции
python migrations/add_natal_chart_fields.py

# Откат миграции
python migrations/add_natal_chart_fields.py downgrade
```

### Вариант 3: Автоматическое создание (для новых БД)

Если база данных пустая, SQLAlchemy автоматически создаст все таблицы с нужными полями при запуске:

```python
Base.metadata.create_all(bind=engine)
```

Это выполняется в `main.py` при старте приложения.

## Структура миграций

### Alembic миграция

**Файл:** `alembic/versions/001_add_natal_chart_fields.py`

Добавляет:
- `users.birth_time_utc` (DateTime, nullable)
- `natal_charts_natalchart.houses_system` (String(20), default='placidus')
- `natal_charts_natalchart.zodiac_type` (String(10), default='tropical')
- `natal_charts_planetposition.is_retrograde` (Integer, default=0)

### Ручная миграция

**Файл:** `migrations/add_natal_chart_fields.py`

Альтернативный способ применения миграций без Alembic.

## Проверка применения миграций

### Через SQL

```sql
-- Проверить поля в users
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'birth_time_utc';

-- Проверить поля в natal_charts_natalchart
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'natal_charts_natalchart' 
AND column_name IN ('houses_system', 'zodiac_type');

-- Проверить поля в natal_charts_planetposition
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'natal_charts_planetposition' 
AND column_name = 'is_retrograde';
```

### Через Python

```python
from database.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)

# Проверка users
users_columns = [col['name'] for col in inspector.get_columns('users')]
assert 'birth_time_utc' in users_columns

# Проверка natal_charts_natalchart
chart_columns = [col['name'] for col in inspector.get_columns('natal_charts_natalchart')]
assert 'houses_system' in chart_columns
assert 'zodiac_type' in chart_columns

# Проверка natal_charts_planetposition
planet_columns = [col['name'] for col in inspector.get_columns('natal_charts_planetposition')]
assert 'is_retrograde' in planet_columns
```

## Создание новых миграций

### Автоматическое определение изменений

```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Ручное создание

```bash
alembic revision -m "Описание изменений"
```

Затем отредактируйте файл в `alembic/versions/`.

## Важные замечания

1. **Безопасность данных**: Миграции проверяют существование таблиц и колонок перед изменением
2. **Idempотентность**: Миграции можно запускать многократно без ошибок
3. **Откат**: Все миграции имеют функцию `downgrade()` для отката изменений
4. **Резервное копирование**: Перед применением миграций рекомендуется сделать резервную копию БД

