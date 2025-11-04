# Инструкция по установке на Windows

## Проблема с pyswisseph

Пакет `pyswisseph` требует компиляции на Windows, что может вызвать ошибки при установке.

## Решения

### Вариант 1: Установка Visual C++ Build Tools (Рекомендуется)

1. Скачайте и установите **Microsoft Visual C++ Build Tools**:
   - Ссылка: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - При установке выберите "C++ build tools" workload

2. После установки перезапустите терминал и попробуйте установить зависимости:
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

### Вариант 2: Использование предварительно скомпилированных wheels

Если установка Build Tools не подходит, можно попробовать использовать предварительно скомпилированные wheels:

1. Обновите pip:
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   ```

2. Попробуйте установить pyswisseph отдельно:
   ```bash
   pip install pyswisseph==2.10.3.2 --only-binary :all:
   ```

3. Если это не сработает, попробуйте установить без привязки к версии:
   ```bash
   pip install pyswisseph --only-binary :all:
   ```

### Вариант 3: Использование conda (Альтернатива)

Если у вас установлен Anaconda или Miniconda:

```bash
conda install -c conda-forge pyswisseph
pip install -r requirements.txt
```

### Вариант 4: Использование более старой версии Python

Если вы используете Python 3.12 или новее, попробуйте использовать Python 3.11 или 3.10, для которых могут быть доступны предварительно скомпилированные wheels.

## Проверка установки

После успешной установки проверьте:

```python
import swisseph as swe
print("pyswisseph установлен успешно!")
```


