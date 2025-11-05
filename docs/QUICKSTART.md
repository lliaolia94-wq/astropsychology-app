# Быстрый старт системы управления контекстом

## Шаг 1: Проверка зависимостей

Перед запуском проверьте, что все компоненты доступны:

```bash
python check_dependencies.py
```

Скрипт покажет:
- ✅ Что работает
- ❌ Что нужно исправить
- ⚠️ Предупреждения

## Шаг 2: Запуск Docker контейнеров (если нужно)

### Redis
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

### Qdrant
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

## Шаг 3: Запуск системы

### Вариант A: Автоматический запуск (рекомендуется)

```bash
python start_all.py
```

Это запустит:
- API сервер на http://localhost:8000
- Context Worker для обработки задач

### Вариант B: Ручной запуск

#### Терминал 1: API сервер
```bash
uvicorn main:app --reload
```

#### Терминал 2: Context Worker
```bash
python run_context_worker.py
```

## Проверка работы

1. Откройте документацию API: http://localhost:8000/docs
2. Проверьте статус worker'а в терминале
3. Отправьте тестовый запрос через API

## Решение проблем

### Redis недоступен
```bash
# Проверьте, запущен ли Redis
docker ps | grep redis

# Если нет, запустите:
docker start redis
# или
docker run -d -p 6379:6379 redis:latest
```

### Qdrant недоступен
```bash
# Проверьте, запущен ли Qdrant
docker ps | grep qdrant

# Если нет, запустите:
docker start qdrant
# или
docker run -d -p 6333:6333 qdrant/qdrant
```

### Модель эмбеддингов не загружается
- Проверьте интернет-соединение (первая загрузка требует интернет)
- Проверьте место на диске (модель ~400MB)
- Модель загрузится автоматически при первом использовании

### Worker не обрабатывает задачи
1. Проверьте, что Redis доступен
2. Проверьте, что worker запущен
3. Проверьте логи worker'а

## Остановка

Нажмите `Ctrl+C` в терминалах или используйте:

```bash
# Остановка Docker контейнеров
docker stop redis qdrant
```

## Полезные команды

```bash
# Проверка зависимостей
python check_dependencies.py

# Запуск всех компонентов
python start_all.py

# Только API сервер
uvicorn main:app --reload

# Только Worker
python run_context_worker.py

# Проверка статуса Docker контейнеров
docker ps

# Просмотр логов Redis
docker logs redis

# Просмотр логов Qdrant
docker logs qdrant
```

