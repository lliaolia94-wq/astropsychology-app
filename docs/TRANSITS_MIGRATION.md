# Миграция транзитов на регистры

## Обзор

Старые endpoints для получения транзитов были удалены и заменены на новые, которые используют `TransitsRegister` для хранения и получения данных.

## Изменения

### Удаленные endpoints

- ❌ `GET /api/professional-calendar/{user_id}/{year}/{month}` - удален
- ❌ `GET /api/daily-transits/{user_id}/{date}` - удален

### Новые endpoints

- ✅ `GET /registers/transits/calendar/{user_id}/{year}/{month}` - календарь транзитов на месяц
- ✅ `GET /registers/transits/daily/{user_id}/{date}` - детальные транзиты на день

## Преимущества новой системы

1. **Хранение данных** - транзиты сохраняются в регистре для быстрого доступа
2. **Автоматический расчет** - если транзитов нет в регистре, они автоматически рассчитываются и сохраняются
3. **Ссылочная целостность** - все транзиты связаны с пользователем через `user_id`
4. **Единая точка доступа** - все транзиты доступны через `/registers/transits`

## Как это работает

### Календарь транзитов

```bash
GET /registers/transits/calendar/{user_id}/{year}/{month}
```

**Логика работы:**
1. Проверяет наличие транзитов в регистре за указанный месяц
2. Если транзитов нет, автоматически рассчитывает их для каждого дня месяца
3. Сохраняет рассчитанные транзиты в регистр
4. Возвращает календарь в том же формате, что и старый endpoint

**Пример ответа:**
```json
{
  "user_id": 1,
  "user_name": "Иван Иванов",
  "calendar": {
    "month": "2024-12",
    "year": 2024,
    "days": [
      {
        "date": "2024-12-01",
        "color": "green",
        "description": "Нейтральный день...",
        "transits": {...}
      }
    ]
  }
}
```

### Детальные транзиты на день

```bash
GET /registers/transits/daily/{user_id}/{date}
```

**Логика работы:**
1. Проверяет наличие транзитов в регистре на указанную дату
2. Если транзитов нет, автоматически рассчитывает их
3. Сохраняет рассчитанные транзиты в регистр
4. Возвращает транзиты в том же формате, что и старый endpoint

**Пример ответа:**
```json
{
  "user_id": 1,
  "date": "2024-12-15",
  "location": {
    "type": "current",
    "name": "Москва",
    "country": "Россия",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "timezone": "Europe/Moscow"
  },
  "transits": {
    "success": true,
    "date": "2024-12-15",
    "transits": {...},
    "summary": "..."
  }
}
```

## Автоматическое сохранение транзитов

При первом запросе транзитов для даты:

1. Система проверяет наличие транзитов в `TransitsRegister`
2. Если транзитов нет, вызывается `astro_service.calculate_transits()`
3. Рассчитанные транзиты сохраняются в регистр с полной информацией:
   - Период действия транзита
   - Уровень влияния (low, medium, high, critical)
   - Области влияния (career, relationships, finance, spiritual)
   - Интерпретация
   - Точное время аспекта

## Миграция клиентского кода

### Старый код

```python
# Старый способ
response = requests.get(f"/api/professional-calendar/{user_id}/2024/12")
response = requests.get(f"/api/daily-transits/{user_id}/2024-12-15")
```

### Новый код

```python
# Новый способ
response = requests.get(f"/registers/transits/calendar/{user_id}/2024/12")
response = requests.get(f"/registers/transits/daily/{user_id}/2024-12-15")
```

## Преимущества для производительности

- **Кэширование** - транзиты рассчитываются один раз и сохраняются
- **Быстрый доступ** - последующие запросы получают данные из БД без пересчета
- **Масштабируемость** - можно предварительно рассчитать транзиты на год вперед

## Предварительный расчет транзитов

Для оптимизации можно создать задачу, которая будет рассчитывать транзиты заранее:

```python
from app.services.registers_service import registers_service
from datetime import date, timedelta

# Рассчитать транзиты на месяц вперед
start_date = date.today()
for i in range(30):
    target_date = start_date + timedelta(days=i)
    registers_service.calculate_and_save_transits_for_date(
        db=db,
        user=user,
        target_date=target_date
    )
```

## Обратная совместимость

Формат ответа новых endpoints полностью совместим со старыми:

- Структура данных идентична
- Поля ответа те же самые
- Обработка ошибок аналогична

Единственное изменение - URL endpoints.

## Обновленные файлы

- ✅ `app/api/v1/endpoints/astrology.py` - удалены старые endpoints
- ✅ `app/api/v1/endpoints/registers.py` - добавлены новые endpoints
- ✅ `app/services/registers_service.py` - добавлены методы расчета и сохранения транзитов
- ✅ `test_requests.http` - обновлены примеры запросов

## Проверка работоспособности

После миграции проверьте:

1. **Календарь:**
   ```bash
   curl http://localhost:8000/registers/transits/calendar/1/2024/12
   ```

2. **Дневные транзиты:**
   ```bash
   curl http://localhost:8000/registers/transits/daily/1/2024-12-15
   ```

3. **Проверка сохранения в БД:**
   ```python
   from app.models.database.models import TransitsRegister
   transits = db.query(TransitsRegister).filter(
       TransitsRegister.user_id == 1,
       TransitsRegister.transit_date == date(2024, 12, 15)
   ).all()
   assert len(transits) > 0
   ```

