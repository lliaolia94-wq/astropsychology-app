# Система управления контекстом общения

## Описание

Система управления контекстом общения реализована согласно ТЗ. Она обеспечивает:
- Управление сессиями общения (4 часа бездействия, ключевые слова)
- Интеллектуальное сохранение контекста с асинхронной обработкой
- Векторный поиск через Qdrant для семантического поиска
- Интеграцию с LLM для структурирования контекста

## Архитектура

### Компоненты

1. **Context API Service** (`routers/context.py`)
   - Синхронные endpoints для управления сессиями и записями
   - Асинхронные endpoints для сохранения и поиска

2. **Context Worker Service** (`services/context_worker.py`)
   - Фоновая обработка задач через RQ
   - Структурирование через LLM
   - Векторизация и сохранение в Qdrant

3. **Vector Service** (`services/vector_service.py`)
   - Интеграция с Qdrant
   - Создание эмбеддингов через sentence-transformers
   - Семантический поиск

4. **Redis Service** (`services/redis_service.py`)
   - Кеширование контекста сессий
   - Очереди задач через RQ

5. **Context Service** (`services/context_service.py`)
   - Логика определения сессий
   - Триггеры сохранения контекста
   - Получение релевантного контекста

## Настройка

### Переменные окружения

Добавьте в `.env`:

```env
# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Опционально

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Опционально

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск Qdrant

```bash
# Docker
docker run -p 6333:6333 qdrant/qdrant

# Или используйте облачный Qdrant
```

### Запуск Redis

```bash
# Docker
docker run -p 6379:6379 redis:latest

# Или используйте локальный Redis
```

### Применение миграций

```bash
alembic upgrade head
```

## Проверка зависимостей

Перед запуском проверьте, что все зависимости установлены и доступны:

```bash
python check_dependencies.py
```

Скрипт проверит:
- ✅ Подключение к базе данных
- ✅ Доступность Redis
- ✅ Доступность Qdrant (опционально)
- ✅ Возможность загрузки модели эмбеддингов
- ✅ Наличие всех необходимых переменных окружения

## Запуск

### Вариант 1: Автоматический запуск всех компонентов

```bash
python start_all.py
```

Этот скрипт:
- Проверит все зависимости
- Запустит API сервер
- Запустит Context Worker
- Покажет статус всех компонентов

### Вариант 2: Ручной запуск

#### 1. Запуск API сервера

```bash
uvicorn main:app --reload
```

#### 2. Запуск Context Worker

В отдельном терминале:

**Windows:**
```bash
python run_context_worker.py
# или
start_worker.bat
```

**Linux/Mac:**
```bash
python3 run_context_worker.py
# или
chmod +x start_worker.sh
./start_worker.sh
```

Или через RQ напрямую:

```bash
rq worker context_tasks --url redis://localhost:6379
```

## API Endpoints

### Управление сессиями

- `GET /api/v1/context/sessions/active` - Получить активную сессию

### Асинхронное сохранение

- `POST /api/v1/context/async/save` - Сохранить контекст асинхронно
- `GET /api/v1/context/async/task/{task_id}` - Статус задачи

### Семантический поиск

- `POST /api/v1/context/async/relevant` - Получить релевантный контекст

### Ручное управление

- `POST /api/v1/context/entries/manual` - Создать ручную запись
- `GET /api/v1/context/entries` - Список записей с фильтрацией
- `PUT /api/v1/context/entries/{entry_id}` - Обновить запись
- `DELETE /api/v1/context/entries/{entry_id}` - Удалить запись

## Логика работы

### Определение сессий

1. **Временной интервал**: 4 часа бездействия → новая сессия
2. **Ключевые слова**: "экстренная помощь", "принятие решения" → новая сессия
3. **Первое сообщение за день**: автоматически новая сессия

### Триггеры сохранения контекста

**Обязательные:**
- Каждые 5 сообщений в сессии
- 30 минут бездействия
- Критические шаблоны ("emergency", "decision")
- Ручное сохранение пользователем

**Опциональные (через LLM):**
- Высокая эмоциональная окраска
- Наличие инсайтов
- Длина сообщения > 200 символов

### Получение релевантного контекста

Для каждого промпта ИИ предоставляется:
1. **3 последние записи** из текущей сессии
2. **5 семантически близких записей** из истории (через векторный поиск)
3. **Все критически важные записи** за 30 дней (priority >= 4)

## Мониторинг

### Проверка очереди задач

```python
from services.redis_service import redis_service
queue_length = redis_service.get_queue_length()
print(f"Задач в очереди: {queue_length}")
```

### Проверка статуса задачи

```bash
curl http://localhost:8000/api/v1/context/async/task/{task_id}
```

## Troubleshooting

### Worker не обрабатывает задачи

1. Проверьте подключение к Redis:
   ```bash
   redis-cli ping
   ```

2. Проверьте, что worker запущен:
   ```bash
   python run_context_worker.py
   ```

3. Проверьте логи worker'а

### Qdrant недоступен

1. Проверьте, что Qdrant запущен:
   ```bash
   curl http://localhost:6333/collections
   ```

2. Проверьте переменные окружения:
   ```env
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   ```

### Ошибки миграции

Если миграция не применяется, проверьте:
1. Правильность DATABASE_URL
2. Права доступа к БД
3. Для SQLite: JSONB не поддерживается, используется JSON

## Производительность

- **Время поиска контекста**: < 500ms (p95)
- **Время обработки задачи**: < 5 минут
- **Размер вектора**: 384 измерения
- **Модель эмбеддингов**: paraphrase-multilingual-MiniLM-L12-v2

## Расширение

### Добавление новых триггеров

В `services/context_service.py` метод `should_save_context()`:
```python
# Добавьте новый триггер
if your_condition:
    return True, "your_trigger_type"
```

### Изменение модели эмбеддингов

В `.env`:
```env
EMBEDDING_MODEL=your-model-name
```

**Важно**: Размерность векторов должна соответствовать настройкам Qdrant!

## Тестирование

```bash
# Запуск тестов
pytest tests/test_context_service.py
```

## Документация API

После запуска сервера:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

