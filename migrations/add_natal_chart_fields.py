"""
Миграция для добавления новых полей в таблицы натальных карт.

Добавляет:
1. birth_time_utc в таблицу users
2. houses_system и zodiac_type в таблицу natal_charts_natalchart
3. is_retrograde в таблицу natal_charts_planetposition
"""
from sqlalchemy import text
from database.database import engine


def upgrade():
    """Применение миграции"""
    with engine.connect() as conn:
        # Проверяем, существует ли таблица users
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            )
        """))
        
        if result.scalar():
            # Проверяем, существует ли поле birth_time_utc
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'birth_time_utc'
                )
            """))
            
            if not result.scalar():
                print("Добавление поля birth_time_utc в таблицу users...")
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN birth_time_utc TIMESTAMP
                """))
                conn.commit()
                print("✅ birth_time_utc добавлено")
            else:
                print("ℹ️ birth_time_utc уже существует")
        
        # Проверяем таблицу natal_charts_natalchart
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'natal_charts_natalchart'
            )
        """))
        
        if result.scalar():
            # Проверяем houses_system
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'natal_charts_natalchart' 
                    AND column_name = 'houses_system'
                )
            """))
            
            if not result.scalar():
                print("Добавление поля houses_system в таблицу natal_charts_natalchart...")
                conn.execute(text("""
                    ALTER TABLE natal_charts_natalchart 
                    ADD COLUMN houses_system VARCHAR(20) DEFAULT 'placidus' NOT NULL
                """))
                conn.commit()
                print("✅ houses_system добавлено")
            
            # Проверяем zodiac_type
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'natal_charts_natalchart' 
                    AND column_name = 'zodiac_type'
                )
            """))
            
            if not result.scalar():
                print("Добавление поля zodiac_type в таблицу natal_charts_natalchart...")
                conn.execute(text("""
                    ALTER TABLE natal_charts_natalchart 
                    ADD COLUMN zodiac_type VARCHAR(10) DEFAULT 'tropical' NOT NULL
                """))
                conn.commit()
                print("✅ zodiac_type добавлено")
        
        # Проверяем таблицу natal_charts_planetposition
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'natal_charts_planetposition'
            )
        """))
        
        if result.scalar():
            # Проверяем is_retrograde
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'natal_charts_planetposition' 
                    AND column_name = 'is_retrograde'
                )
            """))
            
            if not result.scalar():
                print("Добавление поля is_retrograde в таблицу natal_charts_planetposition...")
                conn.execute(text("""
                    ALTER TABLE natal_charts_planetposition 
                    ADD COLUMN is_retrograde INTEGER DEFAULT 0 NOT NULL
                """))
                conn.commit()
                print("✅ is_retrograde добавлено")
            else:
                print("ℹ️ is_retrograde уже существует")
        
        print("\n✅ Миграция завершена")


def downgrade():
    """Откат миграции"""
    with engine.connect() as conn:
        print("Откат миграции...")
        
        # Удаляем поля (с осторожностью!)
        try:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS birth_time_utc"))
            conn.execute(text("ALTER TABLE natal_charts_natalchart DROP COLUMN IF EXISTS houses_system"))
            conn.execute(text("ALTER TABLE natal_charts_natalchart DROP COLUMN IF EXISTS zodiac_type"))
            conn.execute(text("ALTER TABLE natal_charts_planetposition DROP COLUMN IF EXISTS is_retrograde"))
            conn.commit()
            print("✅ Откат выполнен")
        except Exception as e:
            print(f"⚠️ Ошибка при откате: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()

