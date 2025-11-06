"""
Проверка РЕАЛЬНОГО содержимого .env файла напрямую
Без использования dotenv, просто читаем файл
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

print("=" * 70)
print("🔍 ПРЯМАЯ ПРОВЕРКА .env ФАЙЛА (БЕЗ dotenv)")
print("=" * 70)
print(f"\nФайл: {env_file}")
print(f"Существует: {'✅ ДА' if env_file.exists() else '❌ НЕТ'}\n")

if not env_file.exists():
    print("❌ Файл .env не найден!")
    sys.exit(1)

print("=" * 70)
print("ПОЛНОЕ СОДЕРЖИМОЕ ФАЙЛА:")
print("=" * 70)

try:
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"\nВсе содержимое файла ({len(content)} символов):")
        print("-" * 70)
        print(content)
        print("-" * 70)
        
        # Ищем строку с DEEPSEEK_API_KEY
        print("\n" + "=" * 70)
        print("АНАЛИЗ СТРОКИ DEEPSEEK_API_KEY:")
        print("=" * 70)
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'DEEPSEEK_API_KEY' in line.upper():
                print(f"\nСтрока {i}:")
                print(f"  Полная строка: {repr(line)}")
                
                if '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    
                    print(f"  Ключ: {repr(key)}")
                    print(f"  Значение: {repr(value)}")
                    print(f"  Длина значения: {len(value)}")
                    print(f"  Начинается с 'sk-': {'✅ ДА' if value.startswith('sk-') else '❌ НЕТ'}")
                    
                    # Проверяем конкретный ключ пользователя
                    expected_key = "sk-888019144c984d878303305ae31095a9"
                    if value == expected_key:
                        print(f"  ✅ Это правильный ключ!")
                    elif value.startswith("sk-8880"):
                        print(f"  ✅ Начинается правильно (sk-8880...)")
                        print(f"  ⚠️ Но не полностью совпадает с ожидаемым")
                        print(f"  Ожидалось: {expected_key}")
                        print(f"  В файле:   {value}")
                    elif 'your' in value.lower() or 'placeholder' in value.lower():
                        print(f"  ❌❌❌ ЭТО ЗАГЛУШКА! Замените на реальный ключ!")
                    else:
                        print(f"  ⚠️ Неизвестное значение")
                        
except Exception as e:
    print(f"\n❌ Ошибка чтения файла: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ Проверка завершена")
print("=" * 70)

