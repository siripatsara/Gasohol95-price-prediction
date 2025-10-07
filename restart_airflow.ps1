# PowerShell Script to Restart Airflow with Asia/Bangkok Timezone
# รีสตาร์ท Airflow และตรวจสอบการตั้งค่า

Write-Host "🔄 Restarting Airflow containers..." -ForegroundColor Cyan

# Change to perfect directory
Set-Location "E:\year4_1\T.Boat\programs\perfect"

# Stop containers
Write-Host "`n⏸️  Stopping containers..." -ForegroundColor Yellow
docker-compose -f docker-compose-airflow.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Containers stopped successfully" -ForegroundColor Green
    
    # Start containers
    Write-Host "`n▶️  Starting containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose-airflow.yml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Containers started successfully" -ForegroundColor Green
        
        # Wait for services to be ready
        Write-Host "`n⏳ Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
        
        # Show container status
        Write-Host "`n📊 Container Status:" -ForegroundColor Cyan
        docker-compose -f docker-compose-airflow.yml ps
        
        # Show Airflow webserver logs to check timezone
        Write-Host "`n🕐 Checking Airflow Timezone Settings..." -ForegroundColor Cyan
        docker exec perfect_airflow_webserver bash -c "echo 'System Time:' && date && echo 'TZ Variable:' && echo `$TZ"
        
        Write-Host "`n✅ Airflow is ready!" -ForegroundColor Green
        Write-Host "🌐 Access Airflow UI at: http://localhost:8083" -ForegroundColor Cyan
        Write-Host "👤 Username: admin" -ForegroundColor White
        Write-Host "🔑 Password: admin123" -ForegroundColor White
        Write-Host "`n⏰ Schedule: Runs at 00:05 and 12:05 (Asia/Bangkok timezone)" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Failed to start containers" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Failed to stop containers" -ForegroundColor Red
}
