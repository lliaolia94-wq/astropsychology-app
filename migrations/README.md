# Миграции базы данных

## Текущие миграции

### `add_natal_chart_fields.py`

Добавляет новые поля в существующие таблицы:

1. **users.birth_time_utc** - Рассчитанное время рождения в UTC
2. **natal_charts_natalchart.houses_system** - Система домов (по умолчанию 'placidus')
3. **natal_charts_natalchart.zodiac_type** - Тип зодиака (по умолчанию 'tropical')
4. **natal_charts_planetposition.is_retrograde** - Флаг ретроградности (0 или 1)

## Использование

### Применение миграции

```bash
python migrations/add_natal_chart_fields.py
```

### Откат миграции

```bash
python migrations/add_natal_chart_fields.py downgrade
```

## Примечания

- Миграция проверяет существование полей перед добавлением
- Безопасна для повторного запуска (idempотентна)
- Работает только с PostgreSQL (проверка через information_schema)

## Рекомендация: Настройка Alembic

Для более продвинутого управления миграциями рекомендуется использовать Alembic:

```bash
# Установка
pip install alembic

# Инициализация
alembic init alembic

# Создание миграции
alembic revision --autogenerate -m "Add natal chart fields"

# Применение
alembic upgrade head
```

