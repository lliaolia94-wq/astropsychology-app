"""
Скрипт для автоматической загрузки данных о городах из открытых источников.
Использует GeoNames и другие публичные источники.
"""
import json
import csv
import os
import sys
import requests
from pathlib import Path
from typing import Dict, List
import time

# Путь к файлу с БД городов
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CITIES_CSV_PATH = DATA_DIR / "cities.csv"
CITIES_DB_PATH = DATA_DIR / "cities_db.json"

# Создаем директорию data, если её нет
DATA_DIR.mkdir(exist_ok=True)


def download_geonames_cities():
    """
    Скачивает данные о городах из GeoNames.
    Использует публичный файл cities15000.zip (15,000+ городов с населением > 15,000)
    """
    print("🌐 Загрузка данных о городах из GeoNames...")
    
    # URL файла с городами GeoNames (cities15000 - города с населением > 15,000)
    geonames_url = "https://download.geonames.org/export/dump/cities15000.zip"
    
    try:
        print(f"📥 Скачивание файла: {geonames_url}")
        response = requests.get(geonames_url, stream=True, timeout=30)
        response.raise_for_status()
        
        zip_path = DATA_DIR / "cities15000.zip"
        total_size = int(response.headers.get('content-length', 0))
        
        print(f"📦 Размер файла: {total_size / 1024 / 1024:.2f} MB")
        
        with open(zip_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r⏳ Прогресс: {progress:.1f}%", end='', flush=True)
        
        print("\n✅ Файл загружен")
        
        # Распаковываем ZIP
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            print("📂 Распаковка архива...")
            zip_ref.extractall(DATA_DIR)
        
        # Ищем файл с данными
        txt_file = DATA_DIR / "cities15000.txt"
        if txt_file.exists():
            print(f"✅ Найден файл: {txt_file}")
            return convert_geonames_to_csv(txt_file)
        else:
            print("❌ Файл cities15000.txt не найден в архиве")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при загрузке: {e}")
        print("💡 Попробуем альтернативный метод...")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def convert_geonames_to_csv(txt_file: Path) -> bool:
    """
    Конвертирует файл GeoNames в формат CSV.
    Формат GeoNames: geonameid, name, asciiname, alternatenames, latitude, longitude,
    feature class, feature code, country code, cc2, admin1 code, admin2 code,
    admin3 code, admin4 code, population, elevation, dem, timezone, modification date
    """
    print("🔄 Конвертация в CSV формат...")
    
    try:
        cities_data = []
        with open(txt_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line_num % 1000 == 0:
                    print(f"\r⏳ Обработано строк: {line_num}", end='', flush=True)
                
                parts = line.strip().split('\t')
                if len(parts) < 19:
                    continue
                
                try:
                    # Парсим данные GeoNames
                    name = parts[1]  # name
                    country_code = parts[8]  # country code
                    latitude = float(parts[4])
                    longitude = float(parts[5])
                    population = int(parts[14]) if parts[14] else 0
                    timezone = parts[17] if len(parts) > 17 else "UTC"
                    
                    # Пропускаем города с населением < 15,000
                    if population < 15000:
                        continue
                    
                    # Преобразуем код страны в название
                    country_name = get_country_name(country_code)
                    
                    cities_data.append({
                        'name': name,
                        'country': country_name,
                        'latitude': latitude,
                        'longitude': longitude,
                        'timezone': timezone,
                        'population': population
                    })
                except (ValueError, IndexError) as e:
                    continue
        
        print(f"\n✅ Обработано {len(cities_data)} городов")
        
        # Сохраняем в CSV
        print(f"💾 Сохранение в {CITIES_CSV_PATH}...")
        with open(CITIES_CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'country', 'latitude', 'longitude', 'timezone', 'population'])
            writer.writeheader()
            writer.writerows(cities_data)
        
        print(f"✅ Сохранено {len(cities_data)} городов в CSV")
        
        # Удаляем временные файлы
        if (DATA_DIR / "cities15000.zip").exists():
            os.remove(DATA_DIR / "cities15000.zip")
        if txt_file.exists():
            os.remove(txt_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при конвертации: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_country_name(country_code: str) -> str:
    """Преобразует код страны ISO в название"""
    country_map = {
        'RU': 'Россия', 'US': 'США', 'GB': 'Великобритания', 'DE': 'Германия',
        'FR': 'Франция', 'IT': 'Италия', 'ES': 'Испания', 'UA': 'Украина',
        'BY': 'Беларусь', 'KZ': 'Казахстан', 'CN': 'Китай', 'JP': 'Япония',
        'IN': 'Индия', 'TR': 'Турция', 'PL': 'Польша', 'RO': 'Румыния',
        'NL': 'Нидерланды', 'BE': 'Бельгия', 'GR': 'Греция', 'CZ': 'Чехия',
        'PT': 'Португалия', 'SE': 'Швеция', 'HU': 'Венгрия', 'AT': 'Австрия',
        'CH': 'Швейцария', 'BG': 'Болгария', 'DK': 'Дания', 'FI': 'Финляндия',
        'SK': 'Словакия', 'IE': 'Ирландия', 'NO': 'Норвегия', 'HR': 'Хорватия',
        'RS': 'Сербия', 'BA': 'Босния и Герцеговина', 'AL': 'Албания',
        'LT': 'Литва', 'SI': 'Словения', 'LV': 'Латвия', 'EE': 'Эстония',
        'MD': 'Молдова', 'MK': 'Северная Македония', 'ME': 'Черногория',
        'GE': 'Грузия', 'AM': 'Армения', 'AZ': 'Азербайджан', 'UZ': 'Узбекистан',
        'KG': 'Кыргызстан', 'TJ': 'Таджикистан', 'TM': 'Туркменистан',
        'IL': 'Израиль', 'EG': 'Египет', 'SA': 'Саудовская Аравия',
        'AE': 'ОАЭ', 'IQ': 'Ирак', 'IR': 'Иран', 'AF': 'Афганистан',
        'PK': 'Пакистан', 'BD': 'Бангладеш', 'TH': 'Тайланд', 'VN': 'Вьетнам',
        'ID': 'Индонезия', 'MY': 'Малайзия', 'PH': 'Филиппины', 'SG': 'Сингапур',
        'KR': 'Южная Корея', 'AU': 'Австралия', 'NZ': 'Новая Зеландия',
        'CA': 'Канада', 'MX': 'Мексика', 'BR': 'Бразилия', 'AR': 'Аргентина',
        'CL': 'Чили', 'CO': 'Колумбия', 'PE': 'Перу', 'VE': 'Венесуэла',
        'ZA': 'ЮАР', 'NG': 'Нигерия', 'KE': 'Кения', 'EG': 'Египет',
    }
    return country_map.get(country_code, country_code)


def create_sample_cities_csv():
    """
    Создает CSV файл с примерами городов, если автоматическая загрузка не удалась.
    Это fallback вариант.
    """
    print("📝 Создание CSV файла с примерами городов...")
    
    # Используем данные из geocoding_service
    from services.geocoding_service import geocoding_service
    default_cities = geocoding_service._get_default_cities()
    
    cities_data = []
    for city_name, city_info in default_cities.items():
        cities_data.append({
            'name': city_name,
            'country': city_info.get('country', ''),
            'latitude': city_info.get('lat', 0),
            'longitude': city_info.get('lon', 0),
            'timezone': city_info.get('timezone', 'UTC'),
            'population': city_info.get('population', 0)
        })
    
    # Сохраняем в CSV
    with open(CITIES_CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'country', 'latitude', 'longitude', 'timezone', 'population'])
        writer.writeheader()
        writer.writerows(cities_data)
    
    print(f"✅ Создан CSV файл с {len(cities_data)} городами")
    return True


def main():
    """Основная функция"""
    print("=" * 60)
    print("🚀 Автоматическая загрузка данных о городах")
    print("=" * 60)
    
    # Пытаемся скачать из GeoNames
    success = download_geonames_cities()
    
    if not success:
        print("\n⚠️ Автоматическая загрузка не удалась")
        print("💡 Используем базовый набор городов")
        create_sample_cities_csv()
        print("\n📌 Для загрузки полной базы данных:")
        print("   1. Скачайте cities15000.zip вручную с https://download.geonames.org/export/dump/")
        print("   2. Распакуйте cities15000.txt в папку data/")
        print("   3. Запустите: python scripts/convert_geonames.py")
    else:
        print("\n✅ Данные успешно загружены!")
        print(f"📁 Файл сохранен: {CITIES_CSV_PATH}")
        print("\n🔄 Теперь запустите скрипт загрузки в БД:")
        print("   python scripts/load_cities_db.py")


if __name__ == "__main__":
    main()

