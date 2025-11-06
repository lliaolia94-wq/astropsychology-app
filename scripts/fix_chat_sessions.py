"""
Скрипт для быстрого исправления структуры таблицы chat_sessions.
Добавляет недостающие столбцы: is_active, parent_session_id, session_type.
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
is_postgresql = not DATABASE_URL.startswith("sqlite")


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице"""
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(conn, constraint_name: str, table_name: str) -> bool:
    """Проверяет существование ограничения в таблице"""
    if not is_postgresql:
        # Для SQLite проверка ограничений сложнее, пропускаем
        return False
    
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.table_constraints 
            WHERE constraint_name = :constraint_name
            AND table_name = :table_name
        """), {"constraint_name": constraint_name, "table_name": table_name})
        return result.scalar() > 0
    except Exception:
        return False


def main():
    print("🔧 Исправление структуры таблицы chat_sessions...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Проверяем существование таблицы
        inspector = inspect(engine)
        if not inspector.has_table('chat_sessions'):
            print("❌ Таблица chat_sessions не существует!")
            print("   Примените миграции: alembic upgrade head")
            return 1
        
        print("✅ Таблица chat_sessions найдена")
        
        # Используем autocommit режим для избежания проблем с транзакциями
        with engine.connect() as conn:
            # Добавляем is_active
            if not column_exists(engine, 'chat_sessions', 'is_active'):
                print("   Добавляем столбец is_active...")
                try:
                    if is_postgresql:
                        conn.execute(text("""
                            ALTER TABLE chat_sessions 
                            ADD COLUMN is_active INTEGER DEFAULT 1
                        """))
                        conn.execute(text("UPDATE chat_sessions SET is_active = 1 WHERE is_active IS NULL"))
                    else:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN is_active INTEGER DEFAULT 1"))
                        conn.execute(text("UPDATE chat_sessions SET is_active = 1 WHERE is_active IS NULL"))
                    conn.commit()
                    print("   ✅ Столбец is_active добавлен")
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ Ошибка при добавлении is_active: {e}")
                    return 1
            else:
                print("   ✅ Столбец is_active уже существует")
        
        with engine.connect() as conn:
            # Добавляем parent_session_id
            if not column_exists(engine, 'chat_sessions', 'parent_session_id'):
                print("   Добавляем столбец parent_session_id...")
                try:
                    if is_postgresql:
                        conn.execute(text("""
                            ALTER TABLE chat_sessions 
                            ADD COLUMN parent_session_id INTEGER
                        """))
                        conn.commit()
                        # Добавляем внешний ключ отдельно
                        if not constraint_exists(conn, 'fk_chat_sessions_parent', 'chat_sessions'):
                            try:
                                conn.execute(text("""
                                    ALTER TABLE chat_sessions 
                                    ADD CONSTRAINT fk_chat_sessions_parent 
                                    FOREIGN KEY (parent_session_id) REFERENCES chat_sessions(id)
                                """))
                                conn.commit()
                            except Exception as e:
                                print(f"   ⚠️ Не удалось создать внешний ключ (может уже существовать): {e}")
                    else:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN parent_session_id INTEGER"))
                        conn.commit()
                    print("   ✅ Столбец parent_session_id добавлен")
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ Ошибка при добавлении parent_session_id: {e}")
                    return 1
            else:
                print("   ✅ Столбец parent_session_id уже существует")
        
        with engine.connect() as conn:
            # Добавляем session_type
            if not column_exists(engine, 'chat_sessions', 'session_type'):
                print("   Добавляем столбец session_type...")
                try:
                    if is_postgresql:
                        conn.execute(text("""
                            ALTER TABLE chat_sessions 
                            ADD COLUMN session_type VARCHAR(50) DEFAULT 'regular'
                        """))
                        conn.execute(text("UPDATE chat_sessions SET session_type = 'regular' WHERE session_type IS NULL"))
                    else:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN session_type VARCHAR(50) DEFAULT 'regular'"))
                        conn.execute(text("UPDATE chat_sessions SET session_type = 'regular' WHERE session_type IS NULL"))
                    conn.commit()
                    print("   ✅ Столбец session_type добавлен")
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ Ошибка при добавлении session_type: {e}")
                    return 1
            else:
                print("   ✅ Столбец session_type уже существует")
        
        print("\n✅ Все необходимые столбцы добавлены!")
        print("\n💡 Рекомендуется также применить миграции для полной синхронизации:")
        print("   alembic upgrade head")
        return 0
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Попробуйте применить миграции вручную:")
        print("   alembic upgrade head")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

