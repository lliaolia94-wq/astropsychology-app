"""
Скрипт для реорганизации структуры проекта
Перемещает файлы в новую структуру папок и обновляет импорты
"""
import os
import shutil
import re
from pathlib import Path

# Определяем корневую директорию проекта
ROOT_DIR = Path(__file__).parent

# Маппинг старых путей к новым
FILE_MAPPING = {
    # Основные файлы
    "main.py": "app/main.py",
    "config.py": "app/core/config.py",
    
    # Роутеры
    "routers/auth.py": "app/api/v1/endpoints/auth.py",
    "routers/users.py": "app/api/v1/endpoints/users.py",
    "routers/astrology.py": "app/api/v1/endpoints/astrology.py",
    "routers/contacts.py": "app/api/v1/endpoints/contacts.py",
    "routers/ai.py": "app/api/v1/endpoints/ai.py",
    "routers/context.py": "app/api/v1/endpoints/context.py",
    "routers/natal_chart.py": "app/api/v1/endpoints/natal_chart.py",
    "routers/geocoding.py": "app/api/v1/endpoints/geocoding.py",
    "routers/guest.py": "app/api/v1/endpoints/guest.py",
    "routers/general.py": "app/api/v1/endpoints/general.py",
    "routers/__init__.py": "app/api/v1/endpoints/__init__.py",
    
    # Core
    "database/database.py": "app/core/database.py",
    "database/models.py": "app/models/database/models.py",
    "database/__init__.py": "app/models/database/__init__.py",
    
    # Schemas
    "schemas/schemas.py": "app/models/schemas/schemas.py",
    "schemas/__init__.py": "app/models/schemas/__init__.py",
    
    # Services (остаются на месте)
    # "services/": "app/services/",
    
    # Workers
    "services/context_worker.py": "app/workers/context_worker.py",
    "run_context_worker.py": "app/workers/run_context_worker.py",
    "run_sqlite_worker.py": "app/workers/run_sqlite_worker.py",
    "start_worker.bat": "app/workers/start_worker.bat",
    "start_worker.sh": "app/workers/start_worker.sh",
}

# Файлы для перемещения в scripts/
SCRIPTS_FILES = [
    "check_dependencies.py",
    "check_migrations.py",
    "check_migration_005.py",
    "check_users_table.py",
    "fix_users_table.py",
    "apply_migration.py",
    "apply_migration_005.py",
    "apply_migration_005_direct.py",
]

# Файлы для перемещения в docs/
DOCS_FILES = [
    "INSTALL_WINDOWS.md",
    "QUICKSTART.md",
    "README_CACHING.md",
    "README_CONFIG.md",
    "README_CONTEXT_SYSTEM.md",
    "README_GEOCODING.md",
    "README_MIGRATIONS.md",
    "README_MOBILE.md",
    "README_TESTING_SMS_BYPASS.md",
    "README_TESTING.md",
    "README_WEB.md",
    "README_SQLITE_QUEUE.md",
    "FIX_DATABASE.md",
    "APPLY_MIGRATION_005.md",
    "APPLY_MIGRATION_SIMPLE.md",
    "RESTRUCTURE_PLAN.md",
]

# Паттерны импортов для замены
IMPORT_REPLACEMENTS = [
    # Старые импорты роутеров
    (r"from routers\.", "from app.api.v1.endpoints."),
    (r"import routers\.", "import app.api.v1.endpoints."),
    
    # Старые импорты database
    (r"from database\.database import", "from app.core.database import"),
    (r"from database\.models import", "from app.models.database.models import"),
    (r"from database import", "from app.models.database import"),
    
    # Старые импорты schemas
    (r"from schemas\.schemas import", "from app.models.schemas.schemas import"),
    (r"from schemas import", "from app.models.schemas import"),
    
    # Старые импорты services (могут быть относительными)
    (r"from services\.", "from app.services."),
    (r"import services\.", "import app.services."),
    
    # Контекстный worker
    (r"from services\.context_worker import", "from app.workers.context_worker import"),
    
    # Импорты из корня (для скриптов)
    (r"from config import", "from app.core.config import"),
]


def create_directory_structure():
    """Создает новую структуру директорий"""
    directories = [
        "app/__init__.py",
        "app/api/__init__.py",
        "app/api/v1/__init__.py",
        "app/api/v1/endpoints",
        "app/core",
        "app/models/__init__.py",
        "app/models/database",
        "app/models/schemas",
        "app/services",
        "app/workers",
        "scripts",
        "docs",
    ]
    
    for dir_path in directories:
        full_path = ROOT_DIR / dir_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if dir_path.endswith(".py"):
            if not full_path.exists():
                full_path.write_text('"""Auto-generated"""\n')
        print(f"✅ Создана структура: {dir_path}")


def copy_file(src, dst):
    """Копирует файл с созданием директорий"""
    dst_path = ROOT_DIR / dst
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    src_path = ROOT_DIR / src
    if src_path.exists():
        shutil.copy2(src_path, dst_path)
        print(f"✅ Скопирован: {src} -> {dst}")
        return True
    else:
        print(f"⚠️  Файл не найден: {src}")
        return False


def update_imports_in_file(file_path):
    """Обновляет импорты в файле"""
    file_path = Path(file_path)
    if not file_path.exists():
        return
    
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Применяем замены импортов
        for pattern, replacement in IMPORT_REPLACEMENTS:
            content = re.sub(pattern, replacement, content)
        
        # Специальные случаи для относительных импортов
        if "app/" in str(file_path):
            # Внутри app/ используем относительные импорты где возможно
            rel_path = file_path.relative_to(ROOT_DIR / "app")
            depth = len(rel_path.parts) - 1
            
            # Если файл в endpoints/ и импортирует services
            if "endpoints" in str(file_path):
                content = re.sub(
                    r"from app\.services\.", 
                    "from app.services.",
                    content
                )
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Обновлены импорты: {file_path}")
    except Exception as e:
        print(f"❌ Ошибка обновления {file_path}: {e}")


def move_services():
    """Перемещает все сервисы в app/services/"""
    services_dir = ROOT_DIR / "services"
    target_dir = ROOT_DIR / "app" / "services"
    
    if not services_dir.exists():
        return
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Копируем все файлы из services
    for file_path in services_dir.iterdir():
        if file_path.is_file() and file_path.suffix == ".py":
            if file_path.name != "context_worker.py":  # Уже перемещен
                shutil.copy2(file_path, target_dir / file_path.name)
                print(f"✅ Скопирован сервис: {file_path.name}")
    
    # Копируем __init__.py если есть
    init_file = services_dir / "__init__.py"
    if init_file.exists():
        shutil.copy2(init_file, target_dir / "__init__.py")


def find_all_markdown_files():
    """Находит все .md файлы в корне проекта (кроме README.md)"""
    md_files = []
    for file_path in ROOT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix == ".md":
            # Оставляем README.md в корне, остальные перемещаем
            if file_path.name.lower() != "readme.md":
                md_files.append(file_path.name)
    return md_files


def main():
    """Основная функция реорганизации"""
    print("=" * 60)
    print("🚀 Начинаем реорганизацию структуры проекта")
    print("=" * 60)
    
    # Создаем структуру директорий
    print("\n📁 Создание структуры директорий...")
    create_directory_structure()
    
    # Перемещаем файлы по маппингу
    print("\n📦 Перемещение файлов...")
    for src, dst in FILE_MAPPING.items():
        if copy_file(src, dst):
            # Обновляем импорты в перемещенном файле
            update_imports_in_file(ROOT_DIR / dst)
    
    # Перемещаем скрипты
    print("\n📜 Перемещение скриптов...")
    for script_file in SCRIPTS_FILES:
        if (ROOT_DIR / script_file).exists():
            copy_file(script_file, f"scripts/{script_file}")
            update_imports_in_file(ROOT_DIR / "scripts" / script_file)
    
    # Находим и перемещаем все .md файлы автоматически
    print("\n📚 Поиск и перемещение документации...")
    all_md_files = find_all_markdown_files()
    
    # Объединяем с предопределенным списком (для избежания дубликатов)
    doc_files_set = set(DOCS_FILES) | set(all_md_files)
    
    moved_count = 0
    for doc_file in sorted(doc_files_set):
        if (ROOT_DIR / doc_file).exists():
            if copy_file(doc_file, f"docs/{doc_file}"):
                moved_count += 1
    
    if moved_count > 0:
        print(f"✅ Перемещено {moved_count} документационных файлов в docs/")
    else:
        print("⚠️  Документационные файлы не найдены или уже перемещены")
    
    # Перемещаем сервисы
    print("\n🔧 Перемещение сервисов...")
    move_services()
    
    # Обновляем импорты в сервисах
    print("\n🔄 Обновление импортов в сервисах...")
    for py_file in (ROOT_DIR / "app" / "services").rglob("*.py"):
        update_imports_in_file(py_file)
    
    # Обновляем импорты во всех файлах app/
    print("\n🔄 Обновление импортов в app/...")
    for py_file in (ROOT_DIR / "app").rglob("*.py"):
        update_imports_in_file(py_file)
    
    # Создаем __init__.py для endpoints с экспортами
    print("\n📝 Создание __init__.py для endpoints...")
    endpoints_init = ROOT_DIR / "app" / "api" / "v1" / "endpoints" / "__init__.py"
    if endpoints_init.exists():
        init_content = """\"\"\"API v1 Endpoints\"\"\"
from .auth import router as auth_router
from .users import router as users_router
from .astrology import router as astrology_router
from .contacts import router as contacts_router
from .ai import router as ai_router
from .context import router as context_router
from .natal_chart import router as natal_chart_router
from .general import router as general_router

try:
    from .geocoding import router as geocoding_router
except ImportError:
    geocoding_router = None

try:
    from .guest import router as guest_router
except ImportError:
    guest_router = None

__all__ = [
    "auth_router",
    "users_router",
    "astrology_router",
    "contacts_router",
    "ai_router",
    "context_router",
    "natal_chart_router",
    "geocoding_router",
    "guest_router",
    "general_router",
]
"""
        endpoints_init.write_text(init_content, encoding='utf-8')
        print("✅ Создан __init__.py для endpoints")
    
    # Обновляем alembic/env.py
    print("\n🔧 Обновление alembic/env.py...")
    alembic_env = ROOT_DIR / "alembic" / "env.py"
    if alembic_env.exists():
        update_imports_in_file(alembic_env)
        # Исправляем путь для импорта
        content = alembic_env.read_text(encoding='utf-8')
        content = content.replace(
            "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))",
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))"
        )
        content = content.replace(
            "from database.database import Base, engine",
            "from app.core.database import Base, engine"
        )
        content = content.replace(
            "from database.models import *",
            "from app.models.database.models import *"
        )
        alembic_env.write_text(content, encoding='utf-8')
        print("✅ Обновлен alembic/env.py")
    
    print("\n" + "=" * 60)
    print("✅ Реорганизация завершена!")
    print("=" * 60)
    print("\n⚠️  ВАЖНО:")
    print("1. Проверьте импорты вручную")
    print("2. Протестируйте запуск приложения")
    print("3. Обновите пути в конфигурационных файлах (если нужно)")
    print("4. Удалите старые файлы после проверки")


if __name__ == "__main__":
    main()
