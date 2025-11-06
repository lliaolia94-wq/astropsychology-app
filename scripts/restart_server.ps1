# Скрипт для перезапуска FastAPI сервера
Write-Host "🔄 Перезапуск FastAPI сервера..." -ForegroundColor Cyan
Write-Host ""

# Поиск процессов Python с uvicorn или run.py
$processes = Get-Process | Where-Object {
    $_.ProcessName -eq "python" -or $_.ProcessName -eq "pythonw" -or $_.ProcessName -like "*uvicorn*"
} | Where-Object {
    $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*run.py*" -or $_.CommandLine -like "*main.py*"
}

if ($processes) {
    Write-Host "Найдены запущенные процессы сервера:" -ForegroundColor Yellow
    foreach ($proc in $processes) {
        Write-Host "  PID: $($proc.Id) - $($proc.ProcessName)" -ForegroundColor Yellow
        try {
            Stop-Process -Id $proc.Id -Force
            Write-Host "  ✅ Процесс остановлен" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️ Не удалось остановить процесс: $_" -ForegroundColor Red
        }
    }
    Write-Host ""
    Start-Sleep -Seconds 2
} else {
    Write-Host "✅ Сервер не запущен" -ForegroundColor Green
    Write-Host ""
}

Write-Host "🚀 Запуск сервера..." -ForegroundColor Cyan

# Проверяем наличие виртуального окружения
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
    Write-Host "Используется виртуальное окружение: $python" -ForegroundColor Green
} else {
    $python = "python"
    Write-Host "Используется системный Python: $python" -ForegroundColor Yellow
}

# Запускаем сервер в фоновом режиме
$scriptPath = Join-Path $PSScriptRoot ".." "run.py"
$scriptPath = Resolve-Path $scriptPath

Write-Host "Запуск: $python $scriptPath" -ForegroundColor Cyan
Write-Host ""

Start-Process -FilePath $python -ArgumentList $scriptPath -NoNewWindow -PassThru

Write-Host "✅ Сервер запущен!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Для остановки сервера нажмите Ctrl+C в окне с сервером" -ForegroundColor Yellow
Write-Host "   Или используйте: Get-Process | Where-Object {$_.CommandLine -like '*run.py*'} | Stop-Process" -ForegroundColor Yellow

