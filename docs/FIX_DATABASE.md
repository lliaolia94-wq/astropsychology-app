# Исправление структуры базы данных

## Проблема

В базе данных отсутствуют столбцы таблицы `users`, необходимые для работы приложения:
- `phone` (обязательный)
- `password_hash` (обязательный)
- И другие поля

## Решение

Есть несколько способов исправить структуру базы данных:

### Вариант 1: Python скрипт (рекомендуется)

Запустите скрипт `fix_users_table.py`:

```bash
python fix_users_table.py
```

Скрипт автоматически:
- Подключится к базе данных из переменной окружения `DATABASE_URL`
- Проверит существующие столбцы
- Добавит все недостающие столбцы
- Создаст необходимые индексы

### Вариант 2: SQL скрипт напрямую

Если у вас есть доступ к PostgreSQL через psql или другой клиент:

```bash
psql -d your_database -f fix_users_table.sql
```

Или выполните SQL команды из файла `fix_users_table.sql` в вашем SQL клиенте.

### Вариант 3: Alembic миграции

Если у вас установлен Alembic:

```bash
alembic upgrade 002
```

Или используйте скрипт:

```bash
python scripts/run_migrations.py upgrade
```

### Вариант 4: Пересоздание таблиц (⚠️ УДАЛИТ ВСЕ ДАННЫЕ)

Если в базе данных нет важных данных, можно пересоздать таблицы:

1. Откройте `main.py`
2. Раскомментируйте строку:
   ```python
   recreate_tables()
   ```
3. Запустите приложение один раз
4. Закомментируйте строку обратно

**ВНИМАНИЕ:** Это удалит все существующие данные!

## Проверка

После применения любого из решений, проверьте:

1. Перезапустите сервер
2. Попробуйте создать контакт снова
3. Если ошибка сохраняется, проверьте логи сервера

## Структура таблицы users

После исправления таблица `users` должна содержать следующие столбцы:

- `id` (INTEGER, PRIMARY KEY)
- `phone` (VARCHAR(20), NOT NULL, UNIQUE)
- `password_hash` (VARCHAR(255), NOT NULL)
- `phone_verified` (INTEGER, DEFAULT 0)
- `name` (VARCHAR(100))
- `birth_date` (VARCHAR(10))
- `birth_time` (VARCHAR(5))
- `birth_place` (VARCHAR(200))
- `birth_date_detailed` (DATE)
- `birth_time_detailed` (TIME)
- `birth_time_utc` (TIMESTAMP)
- `birth_location_name` (VARCHAR(200))
- `birth_country` (VARCHAR(100))
- `birth_latitude` (DECIMAL(9,6))
- `birth_longitude` (DECIMAL(9,6))
- `timezone_name` (VARCHAR(100))
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## Если ничего не помогает

1. Проверьте, что переменная окружения `DATABASE_URL` указывает на правильную базу данных
2. Проверьте логи сервера на наличие других ошибок
3. Убедитесь, что у пользователя базы данных есть права на ALTER TABLE

