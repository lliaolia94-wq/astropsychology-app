# Применение миграции 005 - Добавление поля birth_time_utc_offset

## Способ 1: Использование скрипта Python

Выполните в терминале (активируйте виртуальное окружение, если используете):

```bash
python apply_migration_005.py
```

Или используйте общий скрипт:

```bash
python scripts/run_migrations.py upgrade
```

## Способ 2: Использование Alembic напрямую

Если у вас установлен Alembic в PATH:

```bash
alembic upgrade head
```

Или через Python:

```bash
python -m alembic upgrade head
```

## Способ 3: Прямое выполнение SQL

Если миграции не работают, можно добавить поле напрямую через SQL:

### Для SQLite:
```sql
ALTER TABLE users ADD COLUMN birth_time_utc_offset DECIMAL(5, 2);
```

### Для PostgreSQL:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_time_utc_offset DECIMAL(5, 2);
```

### Для MySQL:
```sql
ALTER TABLE users ADD COLUMN birth_time_utc_offset DECIMAL(5, 2) NULL;
```

## Проверка

После применения миграции проверьте, что поле добавлено:

```sql
-- Для SQLite
PRAGMA table_info(users);

-- Для PostgreSQL
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'birth_time_utc_offset';

-- Для MySQL
DESCRIBE users;
```

## Что делает миграция

Добавляет поле `birth_time_utc_offset` типа `DECIMAL(5, 2)` в таблицу `users` для хранения UTC offset в часах (например, +3.0, -4.0, +3.5). Это поле используется для ручной корректировки времени при проблемах с определением летнего/зимнего времени.

## Откат миграции (если нужно)

Если нужно откатить миграцию:

```bash
alembic downgrade 004
```

Или удалите поле вручную:

```sql
ALTER TABLE users DROP COLUMN birth_time_utc_offset;
```

