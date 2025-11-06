"""
Детальный тест для проверки эндпоинта /ai/chat
С проверкой всех возможных проблем
"""
import requests
import json
import sys

url = "http://localhost:8000/ai/chat"
params = {"user_id": 16}

data = {
    "mentioned_contacts": ["начальник"],
    "message": "Я чувствую напряжение на работе. Какие транзиты влияют?",
    "template_type": "transit_analysis"
}

print("="*70)
print("🧪 ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ ЭНДПОИНТА /ai/chat")
print("="*70)
print(f"\nURL: {url}")
print(f"Params: {params}")
print(f"\nRequest Body:")
print(json.dumps(data, ensure_ascii=False, indent=2))
print("\n" + "="*70 + "\n")

try:
    # Отправка запроса с таймаутом
    print("📤 Отправка запроса...")
    response = requests.post(
        url, 
        params=params, 
        json=data, 
        timeout=60,
        headers={
            "accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    
    print(f"📥 Получен ответ: Status Code = {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("\n" + "-"*70 + "\n")
    
    if response.status_code == 200:
        try:
            result = response.json()
            print("✅ УСПЕШНЫЙ ОТВЕТ:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("\n" + "="*70)
            print("✅ ТЕСТ ПРОЙДЕН УСПЕШНО!")
            print("="*70)
            sys.exit(0)
        except json.JSONDecodeError:
            print("⚠️ Ответ не является валидным JSON:")
            print(response.text[:500])
            sys.exit(1)
    else:
        print(f"❌ ОШИБКА {response.status_code}:")
        try:
            error = response.json()
            print("Response JSON:")
            print(json.dumps(error, ensure_ascii=False, indent=2))
            
            if "detail" in error:
                print("\n" + "="*70)
                print("ДЕТАЛИ ОШИБКИ:")
                print("="*70)
                print(error["detail"])
                print("="*70)
                
                # Проверяем типичные ошибки
                detail = error["detail"]
                if "API ключ" in detail or "DEEPSEEK" in detail.upper():
                    print("\n💡 СОВЕТ: Убедитесь, что DEEPSEEK_API_KEY установлен в .env файле")
                elif "datetime" in detail.lower() or "timezone" in detail.lower():
                    print("\n💡 СОВЕТ: Проверьте настройки timezone в базе данных")
                elif "column" in detail.lower() or "столбец" in detail.lower():
                    print("\n💡 СОВЕТ: Примените миграции базы данных: alembic upgrade head")
                    
        except json.JSONDecodeError:
            print("Response Text (первые 1000 символов):")
            print(response.text[:1000])
        
        print("\n" + "="*70)
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
        print("="*70)
        sys.exit(1)
            
except requests.exceptions.ConnectionError:
    print("❌ Не удалось подключиться к серверу.")
    print("   Убедитесь, что сервер запущен на http://localhost:8000")
    print("   Запустите: python run.py или uvicorn app.main:app --reload")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("❌ Превышено время ожидания ответа (60 секунд)")
    print("   Возможно, API DeepSeek не отвечает или запрос слишком долгий")
    sys.exit(1)
except Exception as e:
    print(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

