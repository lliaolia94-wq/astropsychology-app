"""
Скрипт для установки pyswisseph на Windows с несколькими вариантами.
"""
import subprocess
import sys


def run_command(cmd, description):
    """Выполняет команду и возвращает результат."""
    print(f"\n{'='*60}")
    print(f"Попытка: {description}")
    print(f"Команда: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Успешно!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("✗ Ошибка:")
        print(e.stderr)
        return False


def main():
    print("Установка pyswisseph на Windows")
    print("Этот скрипт попробует несколько методов установки...")
    
    # Метод 1: Обновление pip и setuptools
    print("\n[1/4] Обновление pip и setuptools...")
    run_command(
        f"{sys.executable} -m pip install --upgrade pip setuptools wheel",
        "Обновление pip, setuptools и wheel"
    )
    
    # Метод 2: Попытка установки с предварительно скомпилированными wheels
    print("\n[2/4] Попытка установки с предварительно скомпилированными wheels...")
    if run_command(
        f"{sys.executable} -m pip install pyswisseph==2.10.3.2 --only-binary :all:",
        "Установка pyswisseph с --only-binary"
    ):
        print("\n✓ pyswisseph успешно установлен!")
        return
    
    # Метод 3: Попытка установки без привязки к версии
    print("\n[3/4] Попытка установки без привязки к версии...")
    if run_command(
        f"{sys.executable} -m pip install pyswisseph --only-binary :all:",
        "Установка последней версии pyswisseph"
    ):
        print("\n✓ pyswisseph успешно установлен!")
        return
    
    # Метод 4: Обычная установка (требует компилятор)
    print("\n[4/4] Попытка обычной установки (может потребоваться компилятор)...")
    if run_command(
        f"{sys.executable} -m pip install pyswisseph==2.10.3.2",
        "Обычная установка pyswisseph"
    ):
        print("\n✓ pyswisseph успешно установлен!")
        return
    
    # Если все методы не сработали
    print("\n" + "="*60)
    print("❌ Не удалось установить pyswisseph автоматически.")
    print("\nРекомендуемые решения:")
    print("1. Установите Microsoft Visual C++ Build Tools:")
    print("   https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("2. Используйте conda: conda install -c conda-forge pyswisseph")
    print("3. Попробуйте использовать Python 3.10 или 3.11")
    print("="*60)
    
    # Проверка установки
    print("\nПроверка установки...")
    try:
        import swisseph as swe
        print("✓ pyswisseph установлен и может быть импортирован!")
    except ImportError:
        print("✗ pyswisseph не установлен или не может быть импортирован.")


if __name__ == "__main__":
    main()


