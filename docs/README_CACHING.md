# Кеширование натальных карт

## Описание

Для ускорения доступа к данным натальных карт реализовано in-memory кеширование для GET `/api/natal-chart/` endpoint.

## Особенности

- **Автоматическая инвалидация**: Кеш автоматически обновляется при пересчете карты
- **Проверка актуальности**: Кеш проверяет время последнего расчета карты в БД
- **TTL (Time To Live)**: Кеш живет 1 час (3600 секунд) по умолчанию
- **Thread-safe**: Кеш потокобезопасен благодаря использованию Lock

## Использование

Кеширование работает автоматически для всех GET запросов к `/api/natal-chart/`.

### Когда кеш инвалидируется:

1. **При пересчете карты** (`POST /api/natal-chart/calculate/` или `POST /api/natal-chart/recalculate/`)
2. **При обновлении профиля** (если карта пересчитывается автоматически)
3. **По истечении TTL** (1 час по умолчанию)

### Проверка актуальности

Кеш проверяет время последнего расчета карты (`calculated_at`) в базе данных. Если карта была пересчитана после кеширования, кеш автоматически обновляется.

## Конфигурация

### Изменение TTL

В `services/cache_service.py`:

```python
# Изменить TTL на 2 часа (7200 секунд)
natal_chart_cache = NatalChartCache(ttl_seconds=7200)
```

### Отключение кеша

В `services/natal_chart_service.py` метод `get_chart_for_user` имеет параметр `use_cache`:

```python
# Получить данные без кеша
chart_data = natal_chart_service.get_chart_for_user(user, db, use_cache=False)
```

## API

### CacheService

```python
from services.cache_service import natal_chart_cache

# Получить данные из кеша
cached_data = natal_chart_cache.get(user_id, chart_calculated_at)

# Сохранить в кеш
natal_chart_cache.set(user_id, data, chart_calculated_at)

# Инвалидировать кеш для пользователя
natal_chart_cache.invalidate(user_id)

# Очистить весь кеш
natal_chart_cache.clear()

# Получить размер кеша
size = natal_chart_cache.size()

# Очистить устаревшие записи
expired_count = natal_chart_cache.cleanup_expired()
```

## Производительность

### Без кеша

- Запрос к БД для получения карты
- Загрузка связанных таблиц (planets, aspects, houses)
- Преобразование данных
- **Время**: ~50-100ms (зависит от БД)

### С кешем

- Проверка кеша (in-memory)
- Возврат данных
- **Время**: ~1-5ms

**Ускорение**: ~10-50x быстрее

## Мониторинг

Для мониторинга использования кеша можно использовать:

```python
from services.cache_service import natal_chart_cache

# Количество записей в кеше
cache_size = natal_chart_cache.size()

# Очистка устаревших записей
expired = natal_chart_cache.cleanup_expired()
print(f"Удалено {expired} устаревших записей")
```

## Ограничения

1. **In-memory**: Кеш хранится в памяти, поэтому:
   - Не сохраняется между перезапусками приложения
   - Занимает память (примерно 1-5 KB на пользователя)
   - Не работает в распределенных системах без дополнительной настройки

2. **Для распределенных систем** рекомендуется использовать Redis:
   ```python
   # Пример с Redis (не реализовано)
   import redis
   r = redis.Redis(host='localhost', port=6379, db=0)
   ```

## Будущие улучшения

- [ ] Redis кеш для распределенных систем
- [ ] Метрики использования кеша
- [ ] Настраиваемый TTL через переменные окружения
- [ ] Кеширование других эндпоинтов (транзиты, синастрии)

