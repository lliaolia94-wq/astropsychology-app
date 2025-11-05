"""
Скрипт для проверки готовности к применению миграции 005
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Проверка готовности к применению миграции 005")
print("=" * 60)

# Проверка 1: Alembic установлен
print("\n1. Проверка установки Alembic...")
try:
    import alembic
    print(f"   ✅ Alembic установлен (версия: {alembic.__version__})")
except ImportError:
    print("   ❌ Alembic не установлен")
    print("   Установите: pip install alembic")
    sys.exit(1)

# Проверка 2: Файл миграции существует
print("\n2. Проверка файла миграции...")
migration_file = project_root / "alembic" / "versions" / "005_add_birth_time_utc_offset.py"
if migration_file.exists():
    print(f"   ✅ Файл миграции найден: {migration_file}")
else:
    print(f"   ❌ Файл миграции не найден: {migration_file}")
    sys.exit(1)

# Проверка 3: Конфигурация Alembic
print("\n3. Проверка конфигурации Alembic...")
try:
    from alembic.config import Config
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    print("   ✅ Конфигурация Alembic загружена")
except Exception as e:
    print(f"   ❌ Ошибка загрузки конфигурации: {e}")
    sys.exit(1)

# Проверка 4: Подключение к БД
print("\n4. Проверка подключения к БД...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    print(f"   DATABASE_URL: {database_url[:50]}...")
    
    # Пытаемся подключиться
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    with engine.connect() as conn:
        print("   ✅ Подключение к БД успешно")
except Exception as e:
    print(f"   ⚠️ Ошибка подключения к БД: {e}")
    print("   Проверьте DATABASE_URL в .env файле")

# Проверка 5: Таблица users существует
print("\n5. Проверка таблицы users...")
try:
    from sqlalchemy import inspect
    from database.database import engine
    
    inspector = inspect(engine)
    if inspector.has_table('users'):
        print("   ✅ Таблица users существует")
        
        # Проверяем, есть ли уже поле
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'birth_time_utc_offset' in columns:
            print("   ⚠️ Поле birth_time_utc_offset уже существует!")
            print("   Миграция не требуется.")
        else:
            print("   ✅ Поле birth_time_utc_offset отсутствует - миграция нужна")
    else:
        print("   ⚠️ Таблица users не существует")
        print("   Сначала примените предыдущие миграции")
except Exception as e:
    print(f"   ⚠️ Ошибка проверки таблицы: {e}")

# Проверка 6: Текущая версия миграций
print("\n6. Проверка текущей версии миграций...")
try:
    from alembic import command
    from alembic.config import Config
    
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    # Пытаемся получить текущую версию
    try:
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            if current_rev:
                print(f"   Текущая версия: {current_rev}")
            else:
                print("   ⚠️ Миграции не применены (база данных не в версионировании)")
    except Exception as e:
        print(f"   ⚠️ Не удалось определить текущую версию: {e}")
        print("   Это нормально, если база данных еще не версионирована")
except Exception as e:
    print(f"   ⚠️ Ошибка проверки версии: {e}")

print("\n" + "=" * 60)
print("Проверка завершена!")
print("=" * 60)
print("\nДля применения миграции выполните:")
print("  python apply_migration_005.py")
print("или")
print("  python scripts/run_migrations.py upgrade")
print("\nЕсли миграции не работают, используйте SQL скрипт:")
print("  add_birth_time_utc_offset.sql")

