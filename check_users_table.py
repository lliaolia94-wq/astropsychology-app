"""
Скрипт для проверки структуры таблицы users
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")

print(f"Подключение к базе данных: {database_url[:30]}...")

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import ProgrammingError
    
    if database_url.startswith("sqlite"):
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # Проверяем существование таблицы
        if not inspector.has_table('users'):
            print("❌ Таблица users не существует!")
            sys.exit(1)
        
        print("✅ Таблица users существует")
        
        # Получаем информацию о столбцах
        columns = inspector.get_columns('users')
        print(f"\n📋 Столбцы в таблице users ({len(columns)}):")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get('default') else ""
            print(f"  - {col['name']}: {col['type']} {nullable}{default}")
        
        # Проверяем первичный ключ
        pk_constraint = inspector.get_pk_constraint('users')
        if pk_constraint and pk_constraint.get('constrained_columns'):
            print(f"\n🔑 Первичный ключ: {', '.join(pk_constraint['constrained_columns'])}")
        else:
            print("\n⚠️ ПЕРВИЧНЫЙ КЛЮЧ НЕ НАЙДЕН! Это может быть проблемой.")
        
        # Проверяем индексы
        indexes = inspector.get_indexes('users')
        print(f"\n📊 Индексы ({len(indexes)}):")
        for idx in indexes:
            unique = "UNIQUE" if idx.get('unique') else ""
            print(f"  - {idx['name']}: {', '.join(idx['column_names'])} {unique}")
        
        # Проверяем внешние ключи, которые ссылаются на users.id
        print("\n🔗 Таблицы, ссылающиеся на users.id:")
        all_tables = inspector.get_table_names()
        for table_name in all_tables:
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                if fk['referred_table'] == 'users' and 'id' in fk.get('referred_columns', []):
                    print(f"  - {table_name}.{fk['constrained_columns'][0]} -> users.id")
        
        # Проверяем, есть ли данные
        result = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(f"\n📊 Количество записей: {result}")
        
        if result > 0:
            # Показываем первые несколько записей
            result = conn.execute(text("SELECT id, phone, name FROM users LIMIT 5"))
            rows = result.fetchall()
            print("\n📝 Примеры записей:")
            for row in rows:
                print(f"  - ID: {row[0]}, Phone: {row[1]}, Name: {row[2]}")
        
        # Проверяем, есть ли столбец id
        column_names = [col['name'] for col in columns]
        if 'id' not in column_names:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Столбец 'id' отсутствует в таблице users!")
        else:
            print("\n✅ Столбец 'id' существует")
            
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip install sqlalchemy psycopg2-binary python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

