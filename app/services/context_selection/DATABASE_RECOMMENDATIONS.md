# Рекомендации по оптимизации структуры базы данных

Этот документ содержит рекомендации по улучшению структуры базы данных для повышения производительности системы интеллектуального отбора контекста.

## 1. Улучшенная таблица событий

### Текущая структура
Текущая таблица `context_entries` содержит базовые поля, но не оптимизирована для работы модулей отбора контекста.

### Рекомендуемая структура

```sql
CREATE TABLE context_entries_enhanced (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    
    -- Основной контент
    user_message TEXT NOT NULL,
    ai_response TEXT,
    event_description TEXT,
    insight_text TEXT,
    
    -- Метаданные для модулей
    emotional_state VARCHAR(50),
    priority INTEGER DEFAULT 3,
    tags TEXT[],
    category VARCHAR(50),
    
    -- Векторные представления (для поиска)
    content_vector VECTOR(384), -- эмбеддинг основного контента
    emotion_vector VECTOR(128), -- эмбеддинг эмоциональной окраски
    
    -- Временные метки
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Индексы для быстрого поиска
    INDEX idx_user_time (user_id, created_at DESC),
    INDEX idx_emotional (user_id, emotional_state),
    INDEX idx_category (user_id, category),
    INDEX idx_tags (user_id, tags),
    
    -- Внешние ключи
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Преимущества:
- **Векторные представления**: Предрассчитанные эмбеддинги для быстрого семантического поиска
- **Оптимизированные индексы**: Быстрый поиск по пользователю, времени, эмоциям, категориям
- **Массивы тегов**: Эффективное хранение и поиск по тегам

### Миграция:
```sql
-- Добавление новых полей к существующей таблице
ALTER TABLE context_entries 
ADD COLUMN IF NOT EXISTS content_vector VECTOR(384),
ADD COLUMN IF NOT EXISTS emotion_vector VECTOR(128),
ADD COLUMN IF NOT EXISTS category VARCHAR(50);

-- Создание индексов
CREATE INDEX IF NOT EXISTS idx_user_time ON context_entries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotional ON context_entries(user_id, emotional_state);
CREATE INDEX IF NOT EXISTS idx_category ON context_entries(user_id, category);
CREATE INDEX IF NOT EXISTS idx_tags ON context_entries USING GIN(tags);
```

## 2. Таблица кэшей для производительности

### Назначение
Централизованное хранение кэшированных результатов работы модулей для избежания повторных вычислений.

```sql
CREATE TABLE module_caches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    module_name VARCHAR(50) NOT NULL, -- 'freshness', 'emotions', 'patterns', 'karma'
    cache_key VARCHAR(255) NOT NULL,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Индексы для быстрого поиска
    INDEX idx_module_cache (user_id, module_name, cache_key),
    INDEX idx_cache_expiry (expires_at),
    
    -- Уникальность: один ключ кэша на модуль и пользователя
    UNIQUE(user_id, module_name, cache_key),
    
    -- Внешние ключи
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Использование:
```python
# Пример использования кэша
cache_service.set_cache(
    user_id=123,
    module='freshness',
    key='period_30_days',
    data={'events': [...], 'scores': {...}},
    ttl_hours=24
)

# Получение из кэша
cached_data = cache_service.get_cache(
    user_id=123,
    module='freshness',
    key='period_30_days'
)
```

### Автоматическая очистка:
```sql
-- Удаление устаревших записей (можно запускать по расписанию)
DELETE FROM module_caches WHERE expires_at < NOW();
```

## 3. Специализированные таблицы для модулей

### 3.1. Таблица для модуля свежести

```sql
CREATE TABLE context_entries_freshness (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    time_weight DECIMAL(3,2) NOT NULL,
    priority_weight DECIMAL(3,2) NOT NULL,
    combined_score DECIMAL(3,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    emotional_state VARCHAR(50),
    last_accessed TIMESTAMP,
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_freshness (user_id, combined_score DESC),
    INDEX idx_user_category (user_id, category, combined_score DESC),
    
    FOREIGN KEY (entry_id) REFERENCES context_entries(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 3.2. Таблица для модуля паттернов

```sql
CREATE TABLE user_patterns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    pattern_type VARCHAR(50) NOT NULL, -- 'temporal', 'emotional', 'topical'
    pattern_name VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    frequency INTEGER NOT NULL,
    timeframe_days INTEGER, -- Для временных паттернов
    trigger_conditions JSONB,
    predicted_next_occurrence TIMESTAMP,
    last_detected TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_patterns (user_id, pattern_type, confidence_score DESC),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE pattern_occurrences (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES user_patterns(id) ON DELETE CASCADE,
    entry_id INTEGER NOT NULL,
    occurrence_date TIMESTAMP NOT NULL,
    match_score DECIMAL(3,2) NOT NULL,
    
    INDEX idx_pattern_occurrences (pattern_id, occurrence_date DESC),
    
    FOREIGN KEY (entry_id) REFERENCES context_entries(id) ON DELETE CASCADE
);
```

### 3.3. Таблица для модуля кармы

```sql
CREATE TABLE karmic_themes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    theme_name VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'natal_chart', 'detected', 'user_labeled'
    manifestation_level DECIMAL(3,2) NOT NULL,
    astrological_indicators JSONB, -- Планеты, аспекты, дома
    is_active BOOLEAN DEFAULT TRUE,
    first_detected TIMESTAMP DEFAULT NOW(),
    last_manifested TIMESTAMP,
    
    INDEX idx_user_karmic (user_id, manifestation_level DESC),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE theme_manifestations (
    id SERIAL PRIMARY KEY,
    theme_id INTEGER REFERENCES karmic_themes(id) ON DELETE CASCADE,
    entry_id INTEGER NOT NULL,
    relevance_score DECIMAL(3,2) NOT NULL,
    manifestation_type VARCHAR(50), -- 'challenge', 'lesson', 'growth'
    
    INDEX idx_theme_manifestations (theme_id, relevance_score DESC),
    
    FOREIGN KEY (entry_id) REFERENCES context_entries(id) ON DELETE CASCADE
);
```

## 4. Унифицированный сервисный слой

### Преимущества:
- **Единая точка доступа**: Все модули используют один интерфейс для работы с данными
- **Кэширование**: Автоматическое кэширование результатов
- **Пагинация**: Автоматическая пагинация для больших объемов данных
- **Оптимизация**: Централизованная оптимизация запросов

### Реализация:

См. `app/services/context_selection/data_service.py` для полной реализации.

### Основные методы:

```python
class ContextDataService:
    """Унифицированный сервис для работы с данными контекста"""
    
    def get_entries_for_period(
        self, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[ContextEntry]:
        """Получение событий за период с кэшированием и пагинацией"""
        pass
    
    def get_emotional_entries(
        self, 
        user_id: int, 
        emotion: str, 
        limit: int = 50
    ) -> List[ContextEntry]:
        """Получение событий по эмоциональному состоянию"""
        pass
    
    def get_entries_by_category(
        self,
        user_id: int,
        category: str,
        limit: int = 50
    ) -> List[ContextEntry]:
        """Получение событий по категории"""
        pass
    
    def update_module_cache(
        self,
        user_id: int,
        module: str,
        key: str,
        data: dict,
        ttl_hours: int = 24
    ):
        """Обновление кэша модуля"""
        pass
    
    def get_module_cache(
        self,
        user_id: int,
        module: str,
        key: str
    ) -> Optional[dict]:
        """Получение данных из кэша модуля"""
        pass
```

## 5. Рекомендации по индексам

### Составные индексы для частых запросов:

```sql
-- Для модуля свежести: поиск по пользователю и времени
CREATE INDEX idx_freshness_user_time ON context_entries(user_id, created_at DESC);

-- Для модуля эмоций: поиск по пользователю и эмоции
CREATE INDEX idx_emotions_user_state ON context_entries(user_id, emotional_state);

-- Для модуля паттернов: поиск по пользователю и категории
CREATE INDEX idx_patterns_user_category ON context_entries(user_id, category);

-- Для векторного поиска (если используется pgvector)
CREATE INDEX idx_content_vector ON context_entries USING ivfflat (content_vector vector_cosine_ops);
```

## 6. План миграции

### Этап 1: Подготовка
1. Создать резервную копию текущей базы данных
2. Протестировать миграции на тестовой среде

### Этап 2: Добавление новых полей
1. Добавить векторные поля к существующей таблице
2. Создать новые индексы
3. Заполнить векторные представления для существующих записей

### Этап 3: Создание специализированных таблиц
1. Создать таблицы для кэширования
2. Создать таблицы для модулей (freshness, patterns, karma)
3. Настроить автоматическую очистку устаревших данных

### Этап 4: Внедрение сервисного слоя
1. Реализовать `ContextDataService`
2. Постепенно мигрировать модули на использование сервиса
3. Мониторинг производительности

## 7. Мониторинг и оптимизация

### Метрики для отслеживания:
- Время выполнения запросов
- Использование кэша (hit rate)
- Размер таблиц кэша
- Производительность векторного поиска

### Запросы для анализа:
```sql
-- Размер таблиц
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Использование индексов
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## 8. Заключение

Эти рекомендации помогут:
- **Улучшить производительность**: Предрассчитанные индексы и кэширование
- **Масштабируемость**: Оптимизированные запросы для больших объемов данных
- **Поддерживаемость**: Единый сервисный слой упрощает поддержку кода
- **Гибкость**: Легко добавлять новые модули и оптимизации

