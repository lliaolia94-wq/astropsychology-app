-- Быстрое исправление для добавления недостающих столбцов в chat_sessions
-- Используйте этот скрипт если миграции не могут быть применены автоматически

-- Проверяем и добавляем is_active
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_sessions' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE chat_sessions ADD COLUMN is_active INTEGER DEFAULT 1;
        UPDATE chat_sessions SET is_active = 1 WHERE is_active IS NULL;
    END IF;
END $$;

-- Проверяем и добавляем parent_session_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_sessions' AND column_name = 'parent_session_id'
    ) THEN
        ALTER TABLE chat_sessions ADD COLUMN parent_session_id INTEGER;
        -- Добавляем внешний ключ если его еще нет
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_chat_sessions_parent'
        ) THEN
            ALTER TABLE chat_sessions 
            ADD CONSTRAINT fk_chat_sessions_parent 
            FOREIGN KEY (parent_session_id) REFERENCES chat_sessions(id);
        END IF;
    END IF;
END $$;

-- Проверяем и добавляем session_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_sessions' AND column_name = 'session_type'
    ) THEN
        ALTER TABLE chat_sessions ADD COLUMN session_type VARCHAR(50) DEFAULT 'regular';
    END IF;
END $$;

-- Для SQLite (если используется SQLite вместо PostgreSQL)
-- Раскомментируйте и используйте эти команды для SQLite:

-- ALTER TABLE chat_sessions ADD COLUMN is_active INTEGER DEFAULT 1;
-- UPDATE chat_sessions SET is_active = 1 WHERE is_active IS NULL;

-- ALTER TABLE chat_sessions ADD COLUMN parent_session_id INTEGER;

-- ALTER TABLE chat_sessions ADD COLUMN session_type VARCHAR(50) DEFAULT 'regular';
-- UPDATE chat_sessions SET session_type = 'regular' WHERE session_type IS NULL;

