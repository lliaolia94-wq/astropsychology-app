# Руководство по геокодированию

## Обзор

Система геокодирования использует локальную базу данных городов для поиска координат. При отсутствии города в БД система предлагает ручной ввод координат.

## API Endpoints

### 1. Поиск городов

**POST** `/api/geocoding/search`

Поиск городов для автодополнения в интерфейсе.

**Request:**
```json
{
  "query": "Моск",
  "country": "Россия",
  "limit": 10
}
```

**Response:**
```json
{
  "cities": [
    {
      "location_name": "Москва",
      "lat": 55.7558,
      "lon": 37.6173,
      "country": "Россия",
      "timezone": "Europe/Moscow",
      "population": 12600000
    }
  ],
  "total": 1
}
```

### 2. Геокодирование города

**GET** `/api/geocoding/geocode/{location_name}?country={country}`

Геокодирование города по названию.

**Успешный ответ (200):**
```json
{
  "success": true,
  "data": {
    "location_name": "Москва",
    "lat": 55.7558,
    "lon": 37.6173,
    "country": "Россия",
    "timezone": "Europe/Moscow",
    "population": 12600000
  }
}
```

**Ошибка (404):**
```json
{
  "detail": {
    "error": "Город \"Неизвестный\" не найден в базе данных",
    "error_code": "CITY_NOT_FOUND",
    "requires_manual_input": true,
    "suggestions": [],
    "message": "Город \"Неизвестный\" не найден в базе данных. Пожалуйста, введите координаты вручную через POST /api/geocoding/manual-coordinates"
  }
}
```

### 3. Ручной ввод координат

**POST** `/api/geocoding/manual-coordinates`

Ручной ввод координат, когда город не найден в БД.

**Request:**
```json
{
  "birth_location_name": "Неизвестный город",
  "birth_country": "Россия",
  "birth_latitude": 55.7558,
  "birth_longitude": 37.6173,
  "timezone_name": "Europe/Moscow"
}
```

**Валидация:**
- Широта: от -90 до +90 градусов
- Долгота: от -180 до +180 градусов

**Response:**
Обновленный профиль пользователя (UserResponse)

### 4. Валидация координат

**GET** `/api/geocoding/validate-coordinates?latitude={lat}&longitude={lon}`

Проверка координат без сохранения.

**Response:**
```json
{
  "valid": true,
  "latitude": 55.7558,
  "longitude": 37.6173,
  "timezone": "Europe/Moscow"
}
```

## Обработка ошибок геокодирования

При обновлении профиля через `PATCH /users/me/profile`, если город не найден, возвращается структурированная ошибка:

```json
{
  "detail": {
    "success": false,
    "error": "Город \"Неизвестный\" не найден в базе данных",
    "error_code": "CITY_NOT_FOUND",
    "requires_manual_input": true,
    "suggestions": [
      {
        "location_name": "Москва",
        "lat": 55.7558,
        "lon": 37.6173
      }
    ],
    "message": "Не удалось найти координаты для \"Неизвестный\". Пожалуйста, укажите координаты вручную через API endpoint /api/geocoding/manual-coordinates."
  }
}
```

### Коды ошибок

- `LOCATION_NAME_EMPTY`: Название города не указано
- `CITY_NOT_FOUND`: Город не найден в базе данных

## Расширение базы данных городов

### Текущая БД

По умолчанию используется базовая БД с популярными городами (около 9 городов).

### Расширение до 15,000+ городов

1. **Скачайте данные из GeoNames:**
   - https://www.geonames.org/export/
   - Выберите файл с городами (например, `cities15000.zip`)
   - Распакуйте в `data/cities.csv`

2. **Запустите скрипт загрузки:**
   ```bash
   python scripts/load_cities_db.py
   ```

3. **Формат CSV файла:**
   ```csv
   name,country,latitude,longitude,timezone,population
   Moscow,Russia,55.7558,37.6173,Europe/Moscow,12600000
   ```

4. **Или используйте готовый JSON:**
   Создайте файл `data/cities_db.json` в формате:
   ```json
   {
     "Москва, Россия": {
       "lat": 55.7558,
       "lon": 37.6173,
       "country": "Россия",
       "timezone": "Europe/Moscow",
       "population": 12600000
     }
   }
   ```

## Структура базы данных городов

Каждый город в БД содержит:
- `lat`: Широта (от -90 до +90)
- `lon`: Долгота (от -180 до +180)
- `country`: Название страны
- `timezone`: Временная зона (например, "Europe/Moscow")
- `population`: Население (опционально)

## Примеры использования

### Пример 1: Поиск города

```python
import requests

response = requests.post(
    "http://localhost:8000/api/geocoding/search",
    json={"query": "Моск", "limit": 5}
)
cities = response.json()["cities"]
```

### Пример 2: Ручной ввод координат

```python
response = requests.post(
    "http://localhost:8000/api/geocoding/manual-coordinates",
    headers={"Authorization": "Bearer <token>"},
    json={
        "birth_location_name": "Мой родной город",
        "birth_latitude": 55.7558,
        "birth_longitude": 37.6173,
        "timezone_name": "Europe/Moscow"
    }
)
```

### Пример 3: Обработка ошибки геокодирования

```python
try:
    response = requests.patch(
        "http://localhost:8000/users/me/profile",
        headers={"Authorization": "Bearer <token>"},
        json={
            "birth_location_name": "Неизвестный город"
        }
    )
except requests.exceptions.HTTPError as e:
    error_data = e.response.json()
    if error_data["detail"].get("requires_manual_input"):
        # Показать форму ручного ввода координат
        pass
```

## Временные зоны

Если временная зона не указана, система автоматически определяет её по координатам:
- Для России и близлежащих стран используется приблизительное определение по долготе
- Для других регионов используется UTC (fallback)

Рекомендуется явно указывать `timezone_name` при ручном вводе координат.

