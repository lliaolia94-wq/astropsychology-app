"""
Скрипт для загрузки расширенной базы данных городов (15,000+ городов).
Можно использовать данные из GeoNames или других источников.
"""
import json
import os
import csv
from typing import Dict, List

# Путь к файлу с БД городов
CITIES_DB_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'data',
    'cities_db.json'
)


def load_cities_from_csv(csv_path: str, min_population: int = 50000) -> Dict:
    """
    Загружает города из CSV файла (формат GeoNames).
    
    Формат CSV должен содержать колонки:
    - name: название города
    - country: страна
    - latitude: широта
    - longitude: долгота
    - timezone: временная зона
    - population: население
    """
    cities_db = {}
    
    if not os.path.exists(csv_path):
        print(f"Файл {csv_path} не найден")
        return cities_db
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    population = int(row.get('population', 0))
                    if population < min_population:
                        continue
                    
                    city_name = row.get('name', '').strip()
                    if not city_name:
                        continue
                    
                    # Создаем уникальный ключ: название + страна
                    country = row.get('country', '').strip()
                    city_key = f"{city_name}, {country}" if country else city_name
                    
                    cities_db[city_key] = {
                        'lat': float(row.get('latitude', 0)),
                        'lon': float(row.get('longitude', 0)),
                        'country': country,
                        'timezone': row.get('timezone', 'UTC').strip(),
                        'population': population
                    }
                except (ValueError, KeyError) as e:
                    print(f"Ошибка обработки строки: {e}")
                    continue
        
        print(f"Загружено {len(cities_db)} городов из {csv_path}")
        return cities_db
    
    except Exception as e:
        print(f"Ошибка загрузки CSV: {e}")
        return cities_db


def load_cities_from_json(json_path: str) -> Dict:
    """Загружает города из JSON файла"""
    if not os.path.exists(json_path):
        return {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки JSON: {e}")
        return {}


def save_cities_db(cities_db: Dict, output_path: str = None):
    """Сохраняет базу городов в JSON файл"""
    if output_path is None:
        output_path = CITIES_DB_PATH
    
    # Создаем директорию, если не существует
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cities_db, f, ensure_ascii=False, indent=2)
        print(f"База данных сохранена: {output_path}")
        print(f"Всего городов: {len(cities_db)}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")


def merge_cities_db(existing_db: Dict, new_db: Dict) -> Dict:
    """Объединяет две базы данных городов"""
    merged = existing_db.copy()
    merged.update(new_db)
    return merged


def main():
    """Основная функция для загрузки и сохранения БД городов"""
    print("=" * 60)
    print("🗄️  Загрузка базы данных городов")
    print("=" * 60)
    
    # Загружаем существующую БД (если есть)
    existing_db = load_cities_from_json(CITIES_DB_PATH)
    print(f"📊 Существующая БД: {len(existing_db)} городов")
    
    # Загрузка из CSV (если есть файл)
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cities.csv')
    if os.path.exists(csv_path):
        print(f"\n📁 Найден файл {csv_path}, загружаем города...")
        new_cities = load_cities_from_csv(csv_path, min_population=50000)
        
        if new_cities:
            merged_db = merge_cities_db(existing_db, new_cities)
            save_cities_db(merged_db)
            print(f"✅ Загружено {len(new_cities)} новых городов")
            print(f"✅ Всего в БД: {len(merged_db)} городов")
        else:
            print("⚠️ Новые города не загружены из CSV")
    else:
        print(f"\n📁 Файл {csv_path} не найден")
        print("\n💡 Попробовать автоматически загрузить данные?")
        print("   Запустите: python scripts/download_cities.py")
        print("\n📌 Или вручную:")
        print("1. Скачайте данные из GeoNames: https://www.geonames.org/export/")
        print("   Или используйте другие источники (OpenStreetMap, etc.)")
        print("2. Сохраните в data/cities.csv в формате:")
        print("   name,country,latitude,longitude,timezone,population")
        print("3. Запустите этот скрипт снова")
        print(f"\n📊 Текущая БД содержит {len(existing_db)} городов")


if __name__ == "__main__":
    main()

