"""
Скрипт для конвертации файла GeoNames cities15000.txt в CSV формат.
Используется, если файл cities15000.txt уже скачан вручную.
"""
import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TXT_FILE = DATA_DIR / "cities15000.txt"
CSV_FILE = DATA_DIR / "cities.csv"


def convert_geonames_to_csv():
    """Конвертирует cities15000.txt в CSV"""
    if not TXT_FILE.exists():
        print(f"❌ Файл {TXT_FILE} не найден")
        print("📥 Скачайте cities15000.zip с https://download.geonames.org/export/dump/")
        print("   Распакуйте cities15000.txt в папку data/")
        return False
    
    print(f"🔄 Конвертация {TXT_FILE} в CSV...")
    
    cities_data = []
    with open(TXT_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 1000 == 0:
                print(f"⏳ Обработано: {line_num} строк", end='\r')
            
            parts = line.strip().split('\t')
            if len(parts) < 19:
                continue
            
            try:
                name = parts[1]
                country_code = parts[8]
                latitude = float(parts[4])
                longitude = float(parts[5])
                population = int(parts[14]) if parts[14] else 0
                timezone = parts[17] if len(parts) > 17 else "UTC"
                
                if population < 15000:
                    continue
                
                # Простое преобразование кода страны
                country_name = country_code  # Можно расширить маппинг
                
                cities_data.append({
                    'name': name,
                    'country': country_name,
                    'latitude': latitude,
                    'longitude': longitude,
                    'timezone': timezone,
                    'population': population
                })
            except (ValueError, IndexError):
                continue
    
    print(f"\n✅ Обработано {len(cities_data)} городов")
    
    # Сохраняем в CSV
    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'country', 'latitude', 'longitude', 'timezone', 'population'])
        writer.writeheader()
        writer.writerows(cities_data)
    
    print(f"✅ Сохранено в {CSV_FILE}")
    return True


if __name__ == "__main__":
    convert_geonames_to_csv()

