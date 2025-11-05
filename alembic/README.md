# Миграции Alembic

## Установка Alembic

```bash
pip install -r requirements.txt
```

## Создание новой миграции

```bash
# Автоматическое определение изменений
alembic revision --autogenerate -m "Описание изменений"

# Ручное создание миграции
alembic revision -m "Описание изменений"
```

## Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Применить конкретную миграцию
alembic upgrade <revision_id>

# Откатить последнюю миграцию
alembic downgrade -1

# Откатить все миграции
alembic downgrade base
```

## Проверка статуса

```bash
# Показать текущую версию
alembic current

# Показать историю миграций
alembic history

# Показать SQL без выполнения
alembic upgrade head --sql
```

## Текущие миграции

### 001_add_natal_chart_fields.py

Добавляет следующие поля:

1. **users.birth_time_utc** - DateTime, nullable
2. **natal_charts_natalchart.houses_system** - String(20), default='placidus'
3. **natal_charts_natalchart.zodiac_type** - String(10), default='tropical'
4. **natal_charts_planetposition.is_retrograde** - Integer, default=0

## Примечания

- Миграции проверяют существование таблиц перед добавлением полей
- Безопасны для повторного запуска
- Используют batch_alter_table для совместимости с SQLite и PostgreSQL

