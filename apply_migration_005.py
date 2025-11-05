"""
Скрипт для применения миграции 005 (добавление birth_time_utc_offset в users)
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from alembic.config import Config
    from alembic import command
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Применение миграции 005 (добавление birth_time_utc_offset)...")
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    # Применяем миграцию до версии 005
    command.upgrade(alembic_cfg, "005")
    print("✅ Миграция 005 применена успешно!")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip install alembic")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка при применении миграции: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

