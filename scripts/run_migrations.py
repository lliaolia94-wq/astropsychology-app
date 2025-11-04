"""
Скрипт для применения миграций базы данных.
Использует Alembic для управления миграциями.
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from alembic.config import Config
    from alembic import command
except ImportError:
    print("❌ Alembic не установлен. Установите: pip install alembic")
    sys.exit(1)


def run_migrations():
    """Применяет все миграции"""
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    print("🚀 Применение миграций...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("✅ Миграции применены успешно")
    except Exception as e:
        print(f"❌ Ошибка при применении миграций: {e}")
        sys.exit(1)


def show_current():
    """Показывает текущую версию БД"""
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    try:
        command.current(alembic_cfg)
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def show_history():
    """Показывает историю миграций"""
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    try:
        command.history(alembic_cfg)
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command_name = sys.argv[1]
        
        if command_name == "current":
            show_current()
        elif command_name == "history":
            show_history()
        elif command_name == "upgrade":
            run_migrations()
        else:
            print(f"Неизвестная команда: {command_name}")
            print("Использование: python scripts/run_migrations.py [current|history|upgrade]")
    else:
        run_migrations()

