@echo off
REM Скрипт для применения миграции 005 на Windows
REM Пытается найти Python и запустить миграцию

echo ============================================================
echo Применение миграции 005 - добавление birth_time_utc_offset
echo ============================================================
echo.

REM Пробуем разные варианты Python
set PYTHON_CMD=

REM Вариант 1: python
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_CMD=python
    goto :found
)

REM Вариант 2: python3
where python3 >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_CMD=python3
    goto :found
)

REM Вариант 3: py launcher
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_CMD=py
    goto :found
)

REM Вариант 4: Python в стандартных путях
if exist "C:\Python39\python.exe" (
    set PYTHON_CMD=C:\Python39\python.exe
    goto :found
)
if exist "C:\Python310\python.exe" (
    set PYTHON_CMD=C:\Python310\python.exe
    goto :found
)
if exist "C:\Python311\python.exe" (
    set PYTHON_CMD=C:\Python311\python.exe
    goto :found
)
if exist "C:\Python312\python.exe" (
    set PYTHON_CMD=C:\Python312\python.exe
    goto :found
)

REM Вариант 5: Python в виртуальном окружении
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
    goto :found
)
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
    goto :found
)

REM Python не найден
echo [ОШИБКА] Python не найден!
echo.
echo Используйте один из способов:
echo 1. Установите Python: https://www.python.org/downloads/
echo 2. Выполните SQL напрямую: см. файл add_birth_time_utc_offset.sql
echo 3. Используйте IDE для запуска apply_migration_005_direct.py
echo.
pause
exit /b 1

:found
echo [OK] Найден Python: %PYTHON_CMD%
echo.
echo Запуск миграции...
echo.

%PYTHON_CMD% apply_migration_005_direct.py

if %ERRORLEVEL% == 0 (
    echo.
    echo ============================================================
    echo [УСПЕХ] Миграция применена!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo [ОШИБКА] Миграция не применена
    echo ============================================================
    echo.
    echo Используйте альтернативный способ:
    echo Выполните SQL команду из файла add_birth_time_utc_offset.sql
)

echo.
pause

