# Простое применение миграции 005

## Проблема: Python не найден

Если команда `python` не работает, используйте один из способов ниже.

## Способ 1: Прямое выполнение SQL (САМЫЙ ПРОСТОЙ)

### Для SQLite (по умолчанию в проекте):

1. Найдите файл базы данных (обычно `app.db` в корне проекта)
2. Откройте его в любом SQLite клиенте (например, DB Browser for SQLite, или используйте онлайн SQLite viewer)
3. Выполните команду:

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

## Способ 2: Через FastAPI приложение (если запущено)

Если у вас запущено FastAPI приложение, можно добавить временный endpoint для миграции. Но это не рекомендуется для продакшена.

## Способ 3: Найти правильный путь к Python

Попробуйте найти Python в вашей системе:

1. **Через PowerShell:**
   ```powershell
   Get-Command python* | Select-Object Source
   ```

2. **Проверьте стандартные пути:**
   - `C:\Python39\python.exe`
   - `C:\Python310\python.exe`
   - `C:\Python311\python.exe`
   - `C:\Users\ВашеИмя\AppData\Local\Programs\Python\`

3. **Если Python установлен через Microsoft Store:**
   - Откройте Microsoft Store
   - Найдите "Python" и запустите оттуда

4. **Если Python в виртуальном окружении:**
   - Найдите папку `venv` или `.venv` в проекте
   - Используйте: `venv\Scripts\python.exe apply_migration_005_direct.py`

## Способ 4: Через IDE (PyCharm, VS Code, etc.)

Если вы используете IDE:
1. Откройте файл `apply_migration_005_direct.py`
2. Запустите его через IDE (обычно кнопка "Run" или F5)

## Проверка результата

После применения миграции проверьте, что поле добавлено:

### SQLite:
```sql
PRAGMA table_info(users);
```

Должна быть строка с `birth_time_utc_offset`

### PostgreSQL:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'birth_time_utc_offset';
```

### MySQL:
```sql
DESCRIBE users;
```

## Что делает миграция

Добавляет поле `birth_time_utc_offset` типа `DECIMAL(5, 2)` в таблицу `users`. 
Это поле позволяет вручную указать UTC offset (например, +3.0, -4.0) для корректировки времени при проблемах с определением летнего/зимнего времени.

## Если ничего не помогает

1. Установите Python: https://www.python.org/downloads/
2. Или используйте SQL напрямую (Способ 1) - это самый надежный способ

