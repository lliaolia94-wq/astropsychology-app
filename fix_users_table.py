"""
Скрипт для исправления структуры таблицы users
Добавляет все недостающие столбцы
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных
database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")

print(f"Подключение к базе данных: {database_url[:20]}...")

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import ProgrammingError
    
    # Создаем подключение
    if database_url.startswith("sqlite"):
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # Проверяем существование таблицы
        if not inspector.has_table('users'):
            print("❌ Таблица users не существует!")
            print("Создайте таблицу вручную или используйте Base.metadata.create_all()")
            sys.exit(1)
        
        # Получаем список существующих столбцов
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        print(f"Существующие столбцы: {', '.join(existing_columns)}")
        
        # Определяем столбцы, которые нужно добавить
        columns_to_add = {
            'phone': 'VARCHAR(20)',
            'password_hash': 'VARCHAR(255)',
            'phone_verified': 'INTEGER DEFAULT 0',
            'name': 'VARCHAR(100)',
            'birth_date': 'VARCHAR(10)',
            'birth_time': 'VARCHAR(5)',
            'birth_place': 'VARCHAR(200)',
            'birth_date_detailed': 'DATE',
            'birth_time_detailed': 'TIME',
            'birth_time_utc': 'TIMESTAMP',
            'birth_location_name': 'VARCHAR(200)',
            'birth_country': 'VARCHAR(100)',
            'birth_latitude': 'DECIMAL(9,6)',
            'birth_longitude': 'DECIMAL(9,6)',
            'timezone_name': 'VARCHAR(100)',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
        }
        
        # Определяем, какой SQL использовать (PostgreSQL или SQLite)
        is_postgres = database_url.startswith("postgresql")
        
        # Проверяем, есть ли данные в таблице
        result = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        has_data = result > 0
        print(f"Записей в таблице: {result}")
        
        # Добавляем недостающие столбцы
        added_columns = []
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    # Для PostgreSQL используем ALTER TABLE, для SQLite - специальный синтаксис
                    if is_postgres:
                        # Для NOT NULL столбцов без данных, делаем nullable временно
                        if col_name in ['phone', 'password_hash'] and has_data:
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                        elif col_name == 'phone':
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type} NOT NULL"
                        elif col_name == 'password_hash':
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type} NOT NULL"
                        else:
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    else:
                        # SQLite не поддерживает ALTER TABLE ADD COLUMN с NOT NULL если есть данные
                        sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    
                    conn.execute(text(sql))
                    conn.commit()
                    added_columns.append(col_name)
                    print(f"✅ Добавлен столбец: {col_name}")
                    
                except Exception as e:
                    print(f"❌ Ошибка при добавлении столбца {col_name}: {e}")
                    # Пробуем добавить как nullable
                    if is_postgres and col_name in ['phone', 'password_hash']:
                        try:
                            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                            conn.execute(text(sql))
                            conn.commit()
                            added_columns.append(col_name)
                            print(f"⚠️ Добавлен столбец {col_name} как nullable (нужно заполнить данные)")
                        except Exception as e2:
                            print(f"❌ Не удалось добавить столбец {col_name}: {e2}")
        
        # Создаем индекс для phone, если его нет
        try:
            indexes = [idx['name'] for idx in inspector.get_indexes('users')]
            if 'ix_users_phone' not in indexes:
                if is_postgres:
                    conn.execute(text("CREATE UNIQUE INDEX ix_users_phone ON users (phone)"))
                else:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                conn.commit()
                print("✅ Создан индекс ix_users_phone")
        except Exception as e:
            print(f"⚠️ Ошибка при создании индекса (возможно уже существует): {e}")
        
        if added_columns:
            print(f"\n✅ Успешно добавлено столбцов: {len(added_columns)}")
            print(f"Добавленные столбцы: {', '.join(added_columns)}")
            
            if has_data and ('phone' in added_columns or 'password_hash' in added_columns):
                print("\n⚠️ ВНИМАНИЕ: В таблице есть данные, и были добавлены обязательные столбцы как nullable.")
                print("Необходимо заполнить эти столбцы данными и затем сделать их NOT NULL.")
        else:
            print("\n✅ Все необходимые столбцы уже существуют!")
            
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip install sqlalchemy psycopg2-binary python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

