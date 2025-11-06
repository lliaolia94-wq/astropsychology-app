"""
Тестовый скрипт для проверки эндпоинта /ai/chat после исправления datetime
"""
import requests
import json

url = "http://localhost:8000/ai/chat"
params = {"user_id": 16}

data = {
    "mentioned_contacts": ["начальник"],
    "message": "Я чувствую напряжение на работе. Какие транзиты влияют?",
    "template_type": "transit_analysis"
}

print("🧪 Тестирование эндпоинта /ai/chat после исправления datetime...")
print(f"URL: {url}")
print(f"Params: {params}")
print(f"Data: {json.dumps(data, ensure_ascii=False, indent=2)}")
print("\n" + "="*60 + "\n")

try:
    response = requests.post(url, params=params, json=data, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ УСПЕШНЫЙ ОТВЕТ:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\n✅ Тест пройден успешно!")
    else:
        print(f"❌ ОШИБКА {response.status_code}:")
        try:
            error = response.json()
            print(json.dumps(error, ensure_ascii=False, indent=2))
        except:
            print(response.text)
        print("\n❌ Тест не пройден")
            
except requests.exceptions.ConnectionError:
    print("❌ Не удалось подключиться к серверу.")
    print("   Убедитесь, что сервер запущен на http://localhost:8000")
except requests.exceptions.Timeout:
    print("❌ Превышено время ожидания ответа (30 секунд)")
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()

