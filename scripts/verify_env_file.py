"""
Скрипт для проверки реального содержимого .env файла
Читает файл напрямую без маскирования
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

print("=" * 70)
print("🔍 ПРОВЕРКА РЕАЛЬНОГО СОДЕРЖИМОГО .env ФАЙЛА")
print("=" * 70)
print(f"\nФайл: {env_file}")
print(f"Существует: {'✅ ДА' if env_file.exists() else '❌ НЕТ'}\n")

if not env_file.exists():
    print("❌ Файл .env не найден!")
    sys.exit(1)

print("=" * 70)
print("ПОЛНОЕ СОДЕРЖИМОЕ ФАЙЛА (строки с DEEPSEEK):")
print("=" * 70)

try:
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        found_deepseek = False
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.rstrip()
            
            # Показываем все строки с DEEPSEEK
            if 'DEEPSEEK' in line.upper():
                found_deepseek = True
                print(f"\nСтрока {i}:")
                print(f"  Полная строка: {repr(line_stripped)}")
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    value_stripped = value.strip()
                    
                    print(f"  Ключ: {key.strip()}")
                    print(f"  Значение (полное): {repr(value_stripped)}")
                    print(f"  Значение (без кавычек): {value_stripped}")
                    print(f"  Длина: {len(value_stripped)} символов")
                    print(f"  Начинается с 'sk-': {'✅ ДА' if value_stripped.startswith('sk-') else '❌ НЕТ'}")
                    
                    # Проверяем на заглушки
                    if value_stripped.startswith('your_') or 'your_deeps' in value_stripped.lower():
                        print(f"  ⚠️⚠️⚠️ ВНИМАНИЕ: Это заглушка! Замените на реальный ключ!")
                    elif not value_stripped.startswith('sk-'):
                        print(f"  ⚠️ Ключ должен начинаться с 'sk-'")
                    elif len(value_stripped) < 20:
                        print(f"  ⚠️ Ключ слишком короткий (обычно 40+ символов)")
        
        if not found_deepseek:
            print("\n⚠️ Строки с DEEPSEEK не найдены в файле!")
    
    print("\n" + "=" * 70)
    print("✅ Проверка завершена")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Ошибка чтения файла: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

