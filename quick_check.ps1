# Quick check script หลังตื่นจาก sleep
Write-Host "🔍 Checking Docker Services Status..." -ForegroundColor Cyan

# ตรวจสอบ Docker services
docker-compose -f docker-compose-airflow.yml ps

Write-Host "`n⏰ Current Time:" -ForegroundColor Yellow
Get-Date

Write-Host "`n🌐 Checking Airflow Web UI..." -ForegroundColor Green
Write-Host "Airflow Web UI: http://localhost:8083" -ForegroundColor Blue

Write-Host "`n📊 Next scheduled runs:" -ForegroundColor Magenta
Write-Host "1 AM Daily: Full Oil Price Scraping"
Write-Host "1 PM Daily: Smart Change Detection"

# ตรวจสอบ logs ล่าสุด
Write-Host "`n📝 Latest Airflow Scheduler Logs:" -ForegroundColor Yellow
docker logs perfect_airflow_scheduler --tail 3