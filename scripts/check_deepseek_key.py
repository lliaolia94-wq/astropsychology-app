"""
Скрипт для проверки наличия и валидности DeepSeek API ключа
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
load_dotenv(env_file)

def check_api_key():
    """Проверяет наличие и формат API ключа"""
    print("🔍 Проверка DeepSeek API ключа...")
    print("=" * 60)
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ API ключ не найден!")
        print("\n💡 Решение:")
        print("1. Создайте файл .env в корне проекта")
        print("2. Добавьте строку: DEEPSEEK_API_KEY=sk-ваш_ключ_здесь")
        print("3. Получите ключ на https://platform.deepseek.com/")
        print("\n📖 Подробная инструкция: GET_DEEPSEEK_API_KEY.md")
        return False
    
    # Проверяем формат ключа
    if not api_key.startswith("sk-"):
        print("⚠️ Предупреждение: API ключ должен начинаться с 'sk-'")
        print(f"   Текущий ключ: {api_key[:10]}...")
    
    if len(api_key) < 20:
        print("⚠️ Предупреждение: API ключ кажется слишком коротким")
        print("   Проверьте, что ключ скопирован полностью")
    else:
        print(f"✅ API ключ найден: {api_key[:10]}...{api_key[-4:]}")
        print(f"   Длина ключа: {len(api_key)} символов")
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена!")
    return True

if __name__ == "__main__":
    success = check_api_key()
    sys.exit(0 if success else 1)

