# SQLite Queue - Бесплатная альтернатива Redis для очередей задач

## Описание

SQLite Queue - это бесплатная альтернатива Redis для асинхронной обработки задач. Использует SQLite базу данных для хранения очереди задач и обеспечивает полную асинхронность без необходимости установки Redis.

## Преимущества

✅ **Полностью бесплатно** - не требует Redis или других платных сервисов  
✅ **Работает на Windows** - без необходимости Docker или WSL2  
✅ **Автоматический fallback** - автоматически используется при отсутствии Redis  
✅ **Персистентность** - задачи сохраняются в базе данных  
✅ **Совместимость** - прозрачная замена Redis Queue API  

## Как это работает

1. **При отсутствии Redis** - система автоматически переключается на SQLite очередь
2. **Задачи сохраняются** в таблицу `task_queue` в SQLite базе данных
3. **Worker обрабатывает** задачи из очереди в фоновом режиме
4. **Статусы задач** можно отслеживать через API

## Использование

### Автоматический режим

Система автоматически определяет доступность Redis и переключается на SQLite при необходимости:

```python
# В services/redis_service.py уже настроен автоматический fallback
from services.redis_service import redis_service

# Добавление задачи в очередь (работает с Redis или SQLite)
task_id = redis_service.enqueue_task(
    process_context_save_task,
    session_id=123,
    user_id=1,
    user_message="Привет",
    ai_response="Привет! Как дела?"
)
```

### Запуск Worker

#### Вариант 1: Автоматический (рекомендуется)

Запустите стандартный worker - он автоматически переключится на SQLite при отсутствии Redis:

```bash
python run_context_worker.py
```

#### Вариант 2: Прямой запуск SQLite Worker

Если нужно запустить только SQLite worker:

```bash
python run_sqlite_worker.py
```

### Параметры

Можно настроить через переменные окружения:

```bash
# Имя очереди (по умолчанию: context_tasks)
QUEUE_NAME=context_tasks

# База данных для очереди (используется основная БД если SQLite)
DATABASE_URL=sqlite:///./app.db
```

## API совместимость

SQLite Queue полностью совместим с Redis Queue API:

```python
# Добавление задачи
task_id = redis_service.enqueue_task(func, *args, **kwargs)

# Проверка статуса
status = redis_service.get_job_status(task_id)

# Количество задач в очереди
length = redis_service.get_queue_length()
```

## Структура базы данных

SQLite Queue создает таблицу `task_queue`:

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | ID записи |
| job_id | String(36) | UUID задачи |
| queue_name | String(50) | Имя очереди |
| function_name | String(255) | Имя функции для выполнения |
| args_json | Text | Аргументы в JSON |
| kwargs_json | Text | Keyword arguments в JSON |
| status | String(20) | Статус: queued, started, finished, failed |
| result_json | Text | Результат выполнения |
| error_message | Text | Сообщение об ошибке |
| created_at | DateTime | Время создания |
| started_at | DateTime | Время начала выполнения |
| finished_at | DateTime | Время завершения |
| timeout | Integer | Таймаут в секундах |

## Очистка старых задач

SQLite Queue автоматически не удаляет старые задачи. Для очистки:

```python
from services.sqlite_queue_service import sqlite_queue_service

# Удалить задачи старше 7 дней
sqlite_queue_service.cleanup_old_tasks(days=7)
```

## Производительность

**SQLite Queue vs Redis:**

- ✅ **Простота**: Не требует дополнительных сервисов
- ✅ **Надежность**: Персистентность из коробки
- ⚠️ **Производительность**: Немного медленнее Redis при высокой нагрузке
- ✅ **Достаточно** для большинства проектов

**Рекомендации:**

- Для **высокой нагрузки** (>1000 задач/сек) лучше использовать Redis
- Для **средней/низкой нагрузки** SQLite Queue отлично подходит
- Для **разработки и небольших проектов** SQLite Queue - идеальный выбор

## Миграция с Redis

Если у вас уже работает Redis и вы хотите переключиться на SQLite:

1. Остановите Redis (или просто не запускайте)
2. Запустите SQLite worker: `python run_sqlite_worker.py`
3. Всё работает! API остаётся тем же

Для обратного переключения:
1. Запустите Redis
2. Перезапустите worker
3. Система автоматически переключится на Redis

## Ограничения

1. **Только одна БД**: SQLite не поддерживает множественные подключения на запись одновременно (но это решается через worker)
2. **Локальная БД**: SQLite не подходит для распределенных систем
3. **Производительность**: При очень высокой нагрузке Redis будет быстрее

## Troubleshooting

### Worker не обрабатывает задачи

1. Убедитесь, что worker запущен: `python run_sqlite_worker.py`
2. Проверьте, что есть задачи в очереди:
   ```python
   from services.sqlite_queue_service import sqlite_queue_service
   print(sqlite_queue_service.get_queue_length('context_tasks'))
   ```

### Задачи зависают в статусе "started"

Это может произойти если worker завершился во время выполнения задачи. Перезапустите worker.

### Ошибка "table task_queue already exists"

Это нормально - таблица уже создана. Игнорируйте предупреждение.

## Примеры использования

### Добавление задачи

```python
from services.redis_service import redis_service
from services.context_worker import process_context_save_task

task_id = redis_service.enqueue_task(
    process_context_save_task,
    session_id=1,
    user_id=1,
    user_message="Привет",
    ai_response="Привет!",
    trigger_type="message_count"
)

print(f"Задача добавлена: {task_id}")
```

### Проверка статуса

```python
status = redis_service.get_job_status(task_id)
print(f"Статус: {status['status']}")
print(f"Результат: {status.get('result')}")
```

### Получение статистики

```python
from services.sqlite_queue_service import sqlite_queue_service

# Количество задач в очереди
queued = sqlite_queue_service.get_queue_length('context_tasks')
print(f"Задач в очереди: {queued}")
```

## Лицензия

Этот код является частью проекта Astropsychology App и использует те же лицензионные условия.
