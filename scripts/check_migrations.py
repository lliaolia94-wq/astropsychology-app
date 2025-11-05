"""
Скрипт для проверки наличия всех необходимых полей в базе данных.
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database import engine
from sqlalchemy import inspect, text


def check_field_exists(table_name: str, field_name: str) -> bool:
    """Проверяет существование поля в таблице"""
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return False
        
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return field_name in columns
    except Exception as e:
        print(f"⚠️ Ошибка при проверке {table_name}.{field_name}: {e}")
        return False


def check_migrations():
    """Проверяет наличие всех необходимых полей"""
    print("🔍 Проверка миграций...\n")
    
    results = {
        'users.birth_time_utc': False,
        'natal_charts_natalchart.houses_system': False,
        'natal_charts_natalchart.zodiac_type': False,
        'natal_charts_planetposition.is_retrograde': False,
    }
    
    # Проверяем users.birth_time_utc
    if check_field_exists('users', 'birth_time_utc'):
        results['users.birth_time_utc'] = True
        print("✅ users.birth_time_utc - присутствует")
    else:
        print("❌ users.birth_time_utc - отсутствует")
    
    # Проверяем natal_charts_natalchart
    if check_field_exists('natal_charts_natalchart', 'houses_system'):
        results['natal_charts_natalchart.houses_system'] = True
        print("✅ natal_charts_natalchart.houses_system - присутствует")
    else:
        print("❌ natal_charts_natalchart.houses_system - отсутствует")
    
    if check_field_exists('natal_charts_natalchart', 'zodiac_type'):
        results['natal_charts_natalchart.zodiac_type'] = True
        print("✅ natal_charts_natalchart.zodiac_type - присутствует")
    else:
        print("❌ natal_charts_natalchart.zodiac_type - отсутствует")
    
    # Проверяем natal_charts_planetposition
    if check_field_exists('natal_charts_planetposition', 'is_retrograde'):
        results['natal_charts_planetposition.is_retrograde'] = True
        print("✅ natal_charts_planetposition.is_retrograde - присутствует")
    else:
        print("❌ natal_charts_planetposition.is_retrograde - отсутствует")
    
    print("\n" + "="*50)
    
    if all(results.values()):
        print("✅ Все поля присутствуют в базе данных")
        return 0
    else:
        print("❌ Некоторые поля отсутствуют. Примените миграции:")
        print("   alembic upgrade head")
        print("   или")
        print("   python migrations/add_natal_chart_fields.py")
        return 1


if __name__ == "__main__":
    exit_code = check_migrations()
    sys.exit(exit_code)

