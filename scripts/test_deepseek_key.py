"""
Скрипт для проверки валидности DeepSeek API ключа
Выполняет тестовый запрос к API для проверки
"""
import os
import sys
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
load_dotenv(env_file)

async def test_api_key():
    """Проверяет валидность API ключа через тестовый запрос"""
    print("🔍 Проверка валидности DeepSeek API ключа...")
    print("=" * 60)
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ API ключ не найден в переменных окружения!")
        print("\n💡 Решение:")
        print("1. Создайте файл .env в корне проекта")
        print("2. Добавьте строку: DEEPSEEK_API_KEY=sk-ваш_ключ_здесь")
        print("3. Получите ключ на https://platform.deepseek.com/")
        print("\n📖 Подробная инструкция: GET_DEEPSEEK_API_KEY.md")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Длина ключа: {len(api_key)} символов")
    
    # Проверяем формат
    if not api_key.startswith("sk-"):
        print("⚠️ Предупреждение: API ключ должен начинаться с 'sk-'")
        print(f"   Текущий ключ начинается с: {api_key[:5]}...")
    
    print("\n📤 Отправка тестового запроса к DeepSeek API...")
    
    # Актуальные модели DeepSeek-V3.2-Exp (согласно официальной документации)
    # deepseek-chat - режим без размышлений
    # deepseek-reasoner - режим с размышлениями
    models_to_try = ["deepseek-chat", "deepseek-reasoner"]
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            for model in models_to_try:
                print(f"\n🔄 Пробуем модель: {model}")
                
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Привет! Это тестовый запрос."}
                    ],
                    "max_tokens": 10
                }
                
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Модель {model} работает! API ключ валиден.")
                    print(f"   Ответ: {result.get('choices', [{}])[0].get('message', {}).get('content', '')[:50]}...")
                    print(f"\n💡 Рекомендация: Установите в .env файле:")
                    print(f"   DEEPSEEK_MODEL={model}")
                    return True
                elif response.status_code == 402:
                    print(f"   ⚠️ Недостаточно баланса (402) для модели {model}")
                    print(f"   💡 Пополните баланс на https://platform.deepseek.com/")
                    if model != models_to_try[-1]:
                        print(f"   Пробуем следующую модель...")
                        continue
                    else:
                        print(f"\n❌ Все модели требуют пополнения баланса")
                        print(f"   💡 Решение: Пополните баланс на https://platform.deepseek.com/")
                        return False
                elif response.status_code == 404:
                    print(f"   ❌ Модель {model} не найдена (404)")
                    if model != models_to_try[-1]:
                        print(f"   Пробуем следующую модель...")
                        continue
                    else:
                        print(f"\n❌ Все модели вернули 404 ошибку")
                        print(f"   Возможные причины:")
                        print(f"   1. Неверный URL endpoint")
                        print(f"   2. API ключ не имеет доступа к моделям")
                        print(f"   3. Изменения в API DeepSeek")
                        print(f"\n💡 Попробуйте:")
                        print(f"   1. Проверьте актуальную документацию: https://api-docs.deepseek.com/")
                        print(f"   2. Проверьте доступные модели в личном кабинете: https://platform.deepseek.com/")
                        return False
                elif response.status_code == 401:
                    print("❌ Ошибка авторизации (401)")
                    print("   API ключ недействителен или неправильный")
                    print("\n💡 Возможные причины:")
                    print("1. Ключ скопирован не полностью")
                    print("2. Ключ истек или был удален")
                    print("3. Ключ неверного формата")
                    print("\n💡 Решение:")
                    print("1. Получите новый ключ на https://platform.deepseek.com/")
                    print("2. Убедитесь, что ключ скопирован полностью (начинается с sk-)")
                    print("3. Проверьте, что в .env файле нет лишних пробелов")
                    print(f"   Текущий ключ: {api_key}")
                    return False
                elif response.status_code == 400:
                    # Ошибка запроса (возможно, модель не существует)
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", response.text[:200] if response.text else "Unknown error")
                    print(f"   ❌ Ошибка запроса (400) для модели {model}")
                    print(f"   Сообщение: {error_msg}")
                    if "Model Not Exist" in str(error_msg):
                        print(f"   💡 Модель не существует")
                        if model != models_to_try[-1]:
                            print(f"   Пробуем следующую модель...")
                            continue
                        else:
                            print(f"\n❌ Все модели не существуют")
                            print(f"   💡 Используйте только: deepseek-chat или deepseek-reasoner")
                            return False
                    else:
                        # Другая ошибка 400
                        if model != models_to_try[-1]:
                            print(f"   Пробуем следующую модель...")
                            continue
                        else:
                            return False
                elif response.status_code == 429:
                    print("⚠️ Превышен лимит запросов (429)")
                    print("   API ключ валиден, но лимит исчерпан")
                    print("   Подождите немного и попробуйте снова")
                    return True  # Ключ валиден, просто лимит
                else:
                    print(f"   ❌ Ошибка API: {response.status_code}")
                    print(f"   Ответ: {response.text[:200]}")
                    if model != models_to_try[-1]:
                        print(f"   Пробуем следующую модель...")
                        continue
                    else:
                        return False
                
    except httpx.TimeoutException:
        print("❌ Таймаут при запросе к API")
        print("   Проверьте интернет-соединение")
        return False
    except httpx.RequestError as e:
        print(f"❌ Ошибка соединения: {e}")
        print("   Проверьте интернет-соединение")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    try:
        result = asyncio.run(test_api_key())
        print("\n" + "=" * 60)
        if result:
            print("✅ Проверка завершена успешно!")
        else:
            print("❌ Проверка не пройдена")
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Проверка прервана пользователем")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

