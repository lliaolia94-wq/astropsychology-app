@echo off
echo 🔄 Перезапуск FastAPI сервера...
echo.

REM Поиск и остановка процессов Python с uvicorn
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /C:"python.exe" >nul
if %errorlevel%==0 (
    echo Найдены процессы Python
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *run.py*" >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo 🚀 Запуск сервера...

REM Проверяем виртуальное окружение
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo Используется виртуальное окружение
) else (
    set PYTHON=python
    echo Используется системный Python
)

REM Запускаем сервер
cd /d %~dp0..
%PYTHON% run.py

pause

