"""
Скрипт для быстрого исправления структуры таблицы context_entries.
Добавляет недостающие столбцы из миграции 007.
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
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


def main():
    print("🔧 Исправление структуры таблицы context_entries...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Проверяем существование таблицы
        inspector = inspect(engine)
        if not inspector.has_table('context_entries'):
            print("❌ Таблица context_entries не существует!")
            print("   Примените миграции: alembic upgrade head")
            return 1
        
        print("✅ Таблица context_entries найдена")
        
        # Добавляем session_id (самое важное)
        if not column_exists(engine, 'context_entries', 'session_id'):
            print("   Добавляем столбец session_id...")
            with engine.connect() as conn:
                try:
                    if is_postgresql:
                        conn.execute(text("""
                            ALTER TABLE context_entries 
                            ADD COLUMN session_id INTEGER
                        """))
                        conn.commit()
                        
                        # Связываем существующие записи с сессиями
                        print("   Связываем существующие записи с сессиями...")
                        conn.execute(text("""
                            UPDATE context_entries 
                            SET session_id = (
                                SELECT id FROM chat_sessions 
                                WHERE chat_sessions.user_id = context_entries.user_id 
                                ORDER BY chat_sessions.created_at DESC 
                                LIMIT 1
                            )
                            WHERE session_id IS NULL
                        """))
                        conn.commit()
                        
                        # Создаем временные сессии для записей без сессий
                        print("   Создаем временные сессии для записей без сессий...")
                        conn.execute(text("""
                            INSERT INTO chat_sessions (user_id, title, created_at, updated_at, is_active, session_type)
                            SELECT DISTINCT user_id, 'Legacy Session', NOW(), NOW(), 0, 'regular'
                            FROM context_entries
                            WHERE session_id IS NULL
                            ON CONFLICT DO NOTHING
                        """))
                        conn.commit()
                        
                        conn.execute(text("""
                            UPDATE context_entries 
                            SET session_id = (
                                SELECT id FROM chat_sessions 
                                WHERE chat_sessions.user_id = context_entries.user_id 
                                AND chat_sessions.title = 'Legacy Session'
                                LIMIT 1
                            )
                            WHERE session_id IS NULL
                        """))
                        conn.commit()
                        
                        # Добавляем внешний ключ
                        try:
                            conn.execute(text("""
                                ALTER TABLE context_entries 
                                ADD CONSTRAINT fk_context_entries_session 
                                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
                            """))
                            conn.commit()
                        except Exception as e:
                            print(f"   ⚠️ Не удалось создать внешний ключ (может уже существовать): {e}")
                    else:
                        conn.execute(text("ALTER TABLE context_entries ADD COLUMN session_id INTEGER"))
                        conn.commit()
                        
                        # Для SQLite связываем записи
                        conn.execute(text("""
                            UPDATE context_entries 
                            SET session_id = (
                                SELECT id FROM chat_sessions 
                                WHERE chat_sessions.user_id = context_entries.user_id 
                                ORDER BY chat_sessions.created_at DESC 
                                LIMIT 1
                            )
                            WHERE session_id IS NULL
                        """))
                        conn.commit()
                    
                    print("   ✅ Столбец session_id добавлен")
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ Ошибка при добавлении session_id: {e}")
                    return 1
        else:
            print("   ✅ Столбец session_id уже существует")
        
        # Добавляем остальные поля из миграции 007
        fields_to_add = [
            ('user_message', 'TEXT', None),
            ('ai_response', 'TEXT', None),
            ('emotional_state', 'VARCHAR(100)', None),
            ('event_description', 'TEXT', None),
            ('insight_text', 'TEXT', None),
            ('priority', 'INTEGER', '1'),
            ('entry_type', 'VARCHAR(20)', "'auto'"),
            ('vector_id', 'VARCHAR(36)', None),
            ('updated_at', 'TIMESTAMP', None),
        ]
        
        # Для PostgreSQL используем JSONB для astro_context
        if is_postgresql:
            astro_context_type = 'JSONB'
        else:
            astro_context_type = 'JSON'
        
        fields_to_add.append(('astro_context', astro_context_type, None))
        
        with engine.connect() as conn:
            for field_name, field_type, default_value in fields_to_add:
                if not column_exists(engine, 'context_entries', field_name):
                    print(f"   Добавляем столбец {field_name}...")
                    try:
                        if default_value:
                            if is_postgresql:
                                conn.execute(text(f"""
                                    ALTER TABLE context_entries 
                                    ADD COLUMN {field_name} {field_type} DEFAULT {default_value}
                                """))
                            else:
                                conn.execute(text(f"""
                                    ALTER TABLE context_entries 
                                    ADD COLUMN {field_name} {field_type} DEFAULT {default_value}
                                """))
                        else:
                            conn.execute(text(f"""
                                ALTER TABLE context_entries 
                                ADD COLUMN {field_name} {field_type}
                            """))
                        
                        conn.commit()
                        
                        # Для updated_at устанавливаем значение из created_at
                        if field_name == 'updated_at':
                            conn.execute(text("""
                                UPDATE context_entries 
                                SET updated_at = created_at 
                                WHERE updated_at IS NULL
                            """))
                            conn.commit()
                        
                        print(f"   ✅ Столбец {field_name} добавлен")
                    except Exception as e:
                        conn.rollback()
                        print(f"   ⚠️ Ошибка при добавлении {field_name}: {e}")
                else:
                    print(f"   ✅ Столбец {field_name} уже существует")
        
        print("\n✅ Все необходимые столбцы добавлены!")
        print("\n💡 Рекомендуется также применить миграции для полной синхронизации:")
        print("   alembic upgrade head")
        return 0
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Попробуйте применить миграции вручную:")
        print("   alembic upgrade head")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

