"""
Скрипт для диагностики загрузки переменных окружения
Проверяет откуда берется DEEPSEEK_API_KEY
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("=" * 70)
print("🔍 ДИАГНОСТИКА ЗАГРУЗКИ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
print("=" * 70)
print()

# Проверяем системные переменные ДО загрузки .env
print("1. Системные переменные окружения (ДО загрузки .env):")
sys_key = os.getenv("DEEPSEEK_API_KEY")
if sys_key:
    print(f"   ✅ Найдено: {sys_key[:10]}...{sys_key[-4:]} (длина: {len(sys_key)})")
else:
    print("   ❌ Не найдено")
print()

# Проверяем наличие .env файла
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
print(f"2. Проверка файла .env:")
print(f"   Путь: {env_file}")
print(f"   Существует: {'✅ ДА' if env_file.exists() else '❌ НЕТ'}")
print()

if env_file.exists():
    print("3. Содержимое .env файла (ПОЛНОЕ содержимое строк с DEEPSEEK):")
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            found = False
            for i, line in enumerate(lines, 1):
                if 'DEEPSEEK' in line.upper():
                    # Показываем полное значение для диагностики
                    print(f"   Строка {i}: {line.rstrip()}")
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value_stripped = value.strip()
                        if value_stripped:
                            print(f"      → Ключ: {key.strip()}")
                            print(f"      → Значение: {value_stripped}")
                            print(f"      → Длина: {len(value_stripped)} символов")
                            print(f"      → Начинается с 'sk-': {'✅ ДА' if value_stripped.startswith('sk-') else '❌ НЕТ'}")
                            if value_stripped.startswith('your_') or value_stripped.startswith('your_deeps'):
                                print(f"      ⚠️ ВНИМАНИЕ: Это похоже на заглушку! Замените на реальный ключ!")
                        else:
                            print(f"      ⚠️ Пустое значение!")
                    found = True
            if not found:
                print("   ⚠️ Строка с DEEPSEEK_API_KEY не найдена в файле!")
    except Exception as e:
        print(f"   ❌ Ошибка чтения файла: {e}")
    print()

# Загружаем .env с явным указанием пути
print("4. Загрузка .env файла:")
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)
    print(f"   ✅ Загружен файл: {env_file}")
else:
    load_dotenv(override=True)
    print("   ⚠️ Файл .env не найден, используется загрузка по умолчанию")
print()

# Проверяем переменные ПОСЛЕ загрузки .env
print("5. Переменные окружения ПОСЛЕ загрузки .env:")
env_key = os.getenv("DEEPSEEK_API_KEY")
if env_key:
    print(f"   ✅ Найдено: {env_key[:10]}...{env_key[-4:]} (длина: {len(env_key)})")
    print(f"   Начинается с 'sk-': {'✅ ДА' if env_key.startswith('sk-') else '❌ НЕТ'}")
else:
    print("   ❌ Не найдено")
print()

# Сравниваем
print("6. Сравнение:")
if sys_key and env_key:
    if sys_key == env_key:
        print("   ✅ Системная переменная и .env совпадают")
    else:
        print("   ⚠️ Системная переменная и .env РАЗЛИЧАЮТСЯ!")
        print(f"   Системная: {sys_key[:10]}...{sys_key[-4:]}")
        print(f"   Из .env: {env_key[:10]}...{env_key[-4:]}")
        print("   💡 Используется значение из .env (override=True)")
elif env_key:
    print("   ✅ Ключ найден только в .env файле")
elif sys_key:
    print("   ⚠️ Ключ найден только в системных переменных")
else:
    print("   ❌ Ключ не найден нигде!")
print()

# Проверяем другие возможные .env файлы
print("7. Поиск других .env файлов:")
env_files_found = []
for possible_env in [project_root / ".env.local", 
                     project_root / ".env.production",
                     project_root / ".env.development",
                     project_root / "app" / ".env",
                     project_root.parent / ".env"]:
    if possible_env.exists():
        env_files_found.append(possible_env)
        print(f"   ⚠️ Найден: {possible_env}")

if env_files_found:
    print("   💡 Эти файлы могут перекрывать основной .env!")
else:
    print("   ✅ Других .env файлов не найдено")
print()

# Проверяем .env.example
print("8. Проверка .env.example:")
env_example = project_root / ".env.example"
if env_example.exists():
    print(f"   ✅ Найден: {env_example}")
    print("   💡 Это пример файла, не используется для загрузки")
else:
    print("   ❌ Не найден")
print()

print("=" * 70)
print("✅ Диагностика завершена")
print("=" * 70)
print()
print("💡 РЕКОМЕНДАЦИИ:")
print("1. Убедитесь, что в .env файле стоит РЕАЛЬНЫЙ ключ, начинающийся с 'sk-'")
print("2. Проверьте, что в ключе нет лишних пробелов или кавычек")
print("3. Формат должен быть: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
print("4. После изменения .env перезапустите сервер!")

