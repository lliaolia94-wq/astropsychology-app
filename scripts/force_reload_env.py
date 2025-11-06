"""
Скрипт для принудительной проверки и перезагрузки .env файла
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("=" * 70)
print("🔄 ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА .env ФАЙЛА")
print("=" * 70)
print()

project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

print(f"Проверяем файл: {env_file}")
print(f"Существует: {'✅ ДА' if env_file.exists() else '❌ НЕТ'}")
print()

if not env_file.exists():
    print("❌ Файл .env не найден!")
    sys.exit(1)

# Очищаем переменную окружения если она есть
if "DEEPSEEK_API_KEY" in os.environ:
    del os.environ["DEEPSEEK_API_KEY"]
    print("✅ Очищена системная переменная DEEPSEEK_API_KEY")
    print()

# Загружаем заново
print("Загружаем .env файл...")
load_dotenv(dotenv_path=env_file, override=True)
print(f"✅ Загружен: {env_file}")
print()

# Проверяем результат
api_key = os.getenv("DEEPSEEK_API_KEY")
if api_key:
    print(f"✅ Ключ найден: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Длина: {len(api_key)} символов")
    print(f"   Начинается с 'sk-': {'✅ ДА' if api_key.startswith('sk-') else '❌ НЕТ'}")
    
    # Проверяем что это правильный ключ пользователя
    if api_key == "sk-888019144c984d878303305ae31095a9":
        print("   ✅ Это правильный ключ!")
    elif api_key.startswith("sk-8880"):
        print("   ✅ Начинается правильно (sk-8880...)")
    else:
        print(f"   ⚠️ Не совпадает с ожидаемым ключом")
        print(f"   Ожидалось: sk-888019144c984d878303305ae31095a9")
        print(f"   Получено: {api_key}")
else:
    print("❌ Ключ НЕ найден после загрузки!")
    print()
    print("Проверьте содержимое .env файла:")
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if 'DEEPSEEK' in line.upper():
                    print(f"  Строка {i}: {line.rstrip()}")
    except Exception as e:
        print(f"  Ошибка чтения: {e}")

print()
print("=" * 70)
print("✅ Проверка завершена")
print("=" * 70)
print()
print("💡 Перезапустите сервер чтобы изменения вступили в силу:")
print("   python scripts/restart_server.ps1")
print("   или")
print("   Остановите сервер (Ctrl+C) и запустите заново: python run.py")

