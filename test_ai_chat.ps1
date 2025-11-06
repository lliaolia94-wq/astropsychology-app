# Тестовый скрипт для проверки эндпоинта /ai/chat
Write-Host "🧪 Тестирование эндпоинта /ai/chat..." -ForegroundColor Cyan
Write-Host ""

$url = "http://localhost:8000/ai/chat?user_id=16"
$headers = @{
    "accept" = "application/json"
    "Content-Type" = "application/json"
}
$body = @{
    "mentioned_contacts" = @("начальник")
    "message" = "Я чувствую напряжение на работе. Какие транзиты влияют?"
    "template_type" = "transit_analysis"
} | ConvertTo-Json -Compress

Write-Host "URL: $url" -ForegroundColor Yellow
Write-Host "Body: $body" -ForegroundColor Yellow
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -Method Post -Headers $headers -Body $body -ContentType "application/json" -UseBasicParsing
    
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "✅ УСПЕШНЫЙ ОТВЕТ:" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
    Write-Host ""
    Write-Host "✅ Тест пройден успешно!" -ForegroundColor Green
}
catch {
    Write-Host "❌ ОШИБКА:" -ForegroundColor Red
    Write-Host "Exception Type: $($_.Exception.GetType().FullName)" -ForegroundColor Yellow
    Write-Host "Message: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Status Code: $statusCode" -ForegroundColor Yellow
        
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $responseBody = $reader.ReadToEnd()
        
        Write-Host ""
        Write-Host "Response Body:" -ForegroundColor Yellow
        Write-Host $responseBody -ForegroundColor Red
        
        # Пытаемся распарсить JSON ошибки
        try {
            $errorJson = $responseBody | ConvertFrom-Json
            if ($errorJson.detail) {
                Write-Host ""
                Write-Host "Детали ошибки:" -ForegroundColor Yellow
                Write-Host $errorJson.detail -ForegroundColor Red
            }
        } catch {
            # Не JSON, просто выводим текст
        }
    }
    
    Write-Host ""
    Write-Host "❌ Тест не пройден" -ForegroundColor Red
}

