-- SQL скрипт для добавления недостающих столбцов в таблицу users
-- Используйте этот скрипт, если не можете запустить Python скрипт

-- Для PostgreSQL:

-- Проверьте существование столбцов перед добавлением
-- Если столбец не существует, выполните соответствующий ALTER TABLE

-- Добавление столбца phone (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='phone') THEN
        ALTER TABLE users ADD COLUMN phone VARCHAR(20);
    END IF;
END $$;

-- Добавление столбца password_hash (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='password_hash') THEN
        ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
    END IF;
END $$;

-- Добавление столбца phone_verified (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='phone_verified') THEN
        ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0;
    END IF;
END $$;

-- Добавление столбца name (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='name') THEN
        ALTER TABLE users ADD COLUMN name VARCHAR(100);
    END IF;
END $$;

-- Добавление столбца birth_date (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_date') THEN
        ALTER TABLE users ADD COLUMN birth_date VARCHAR(10);
    END IF;
END $$;

-- Добавление столбца birth_time (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_time') THEN
        ALTER TABLE users ADD COLUMN birth_time VARCHAR(5);
    END IF;
END $$;

-- Добавление столбца birth_place (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_place') THEN
        ALTER TABLE users ADD COLUMN birth_place VARCHAR(200);
    END IF;
END $$;

-- Добавление столбца birth_date_detailed (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_date_detailed') THEN
        ALTER TABLE users ADD COLUMN birth_date_detailed DATE;
    END IF;
END $$;

-- Добавление столбца birth_time_detailed (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_time_detailed') THEN
        ALTER TABLE users ADD COLUMN birth_time_detailed TIME;
    END IF;
END $$;

-- Добавление столбца birth_time_utc (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_time_utc') THEN
        ALTER TABLE users ADD COLUMN birth_time_utc TIMESTAMP;
    END IF;
END $$;

-- Добавление столбца birth_location_name (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_location_name') THEN
        ALTER TABLE users ADD COLUMN birth_location_name VARCHAR(200);
    END IF;
END $$;

-- Добавление столбца birth_country (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_country') THEN
        ALTER TABLE users ADD COLUMN birth_country VARCHAR(100);
    END IF;
END $$;

-- Добавление столбца birth_latitude (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_latitude') THEN
        ALTER TABLE users ADD COLUMN birth_latitude DECIMAL(9,6);
    END IF;
END $$;

-- Добавление столбца birth_longitude (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='birth_longitude') THEN
        ALTER TABLE users ADD COLUMN birth_longitude DECIMAL(9,6);
    END IF;
END $$;

-- Добавление столбца timezone_name (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='timezone_name') THEN
        ALTER TABLE users ADD COLUMN timezone_name VARCHAR(100);
    END IF;
END $$;

-- Добавление столбца created_at (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='created_at') THEN
        ALTER TABLE users ADD COLUMN created_at TIMESTAMP;
    END IF;
END $$;

-- Добавление столбца updated_at (если не существует)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='updated_at') THEN
        ALTER TABLE users ADD COLUMN updated_at TIMESTAMP;
    END IF;
END $$;

-- Создание индекса для phone (если не существует)
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone);

-- Проверка результатов
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;

