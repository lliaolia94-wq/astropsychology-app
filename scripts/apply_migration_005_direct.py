"""
Прямое применение миграции 005 через SQL без Alembic
Используйте этот скрипт, если Alembic не работает
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from sqlalchemy import create_engine, text, inspect
    from database.database import engine
    
    print("=" * 60)
    print("Прямое применение миграции 005")
    print("=" * 60)
    
    # Проверяем, существует ли таблица users
    inspector = inspect(engine)
    if not inspector.has_table('users'):
        print("❌ Таблица users не существует!")
        print("Сначала примените предыдущие миграции")
        sys.exit(1)
    
    print("✅ Таблица users найдена")
    
    # Проверяем, есть ли уже поле
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'birth_time_utc_offset' in columns:
        print("ℹ️ Поле birth_time_utc_offset уже существует")
        print("Миграция не требуется")
        sys.exit(0)
    
    print("Добавление поля birth_time_utc_offset...")
    
    # Получаем тип БД
    database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    
    if 'sqlite' in database_url.lower():
        # SQLite
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN birth_time_utc_offset DECIMAL(5, 2)"))
            conn.commit()
        print("✅ Поле добавлено (SQLite)")
    elif 'postgresql' in database_url.lower():
        # PostgreSQL
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_time_utc_offset DECIMAL(5, 2)"))
            conn.commit()
        print("✅ Поле добавлено (PostgreSQL)")
    elif 'mysql' in database_url.lower():
        # MySQL
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN birth_time_utc_offset DECIMAL(5, 2) NULL"))
            conn.commit()
        print("✅ Поле добавлено (MySQL)")
    else:
        # Общий вариант
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN birth_time_utc_offset DECIMAL(5, 2)"))
            conn.commit()
        print("✅ Поле добавлено")
    
    # Проверяем результат
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'birth_time_utc_offset' in columns:
        print("✅ Миграция применена успешно!")
    else:
        print("❌ Ошибка: поле не было добавлено")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nАльтернативный способ:")
    print("1. Откройте файл add_birth_time_utc_offset.sql")
    print("2. Выполните SQL команду вручную в вашем SQL клиенте")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    print("\nАльтернативный способ:")
    print("1. Откройте файл add_birth_time_utc_offset.sql")
    print("2. Выполните SQL команду вручную в вашем SQL клиенте")
    sys.exit(1)

