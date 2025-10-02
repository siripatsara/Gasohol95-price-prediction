# setup_airflow.ps1
# PowerShell script สำหรับตั้งค่า Airflow บน Windows

Write-Host "=== Setting up Airflow for EPPO Oil Price Scraping ===" -ForegroundColor Green

# สร้าง directories ที่จำเป็น
Write-Host "Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "logs"
New-Item -ItemType Directory -Force -Path "plugins" 
New-Item -ItemType Directory -Force -Path "data"
New-Item -ItemType Directory -Force -Path "backups"

# Copy scraper ไปยัง dags directory
Write-Host "Setting up scraper in dags directory..." -ForegroundColor Yellow
Copy-Item -Path "scraper" -Destination "dags" -Recurse -Force

# Set environment variables
$env:AIRFLOW_HOME = (Get-Location).Path
$env:AIRFLOW__CORE__DAGS_FOLDER = Join-Path (Get-Location).Path "dags"
$env:AIRFLOW__CORE__LOGS_FOLDER = Join-Path (Get-Location).Path "logs"
$env:AIRFLOW__CORE__PLUGINS_FOLDER = Join-Path (Get-Location).Path "plugins"

Write-Host "AIRFLOW_HOME set to: $env:AIRFLOW_HOME" -ForegroundColor Cyan

# Check if virtual environment exists
if (Test-Path "../.venv/Scripts/activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "../.venv/Scripts/activate.ps1"
} else {
    Write-Host "Virtual environment not found. Please make sure you're in the correct directory." -ForegroundColor Red
}

# Initialize Airflow database (if not exists)
if (-not (Test-Path "airflow.db")) {
    Write-Host "Initializing Airflow database..." -ForegroundColor Yellow
    & python -m pip install apache-airflow==2.7.1
    & airflow db init
}

Write-Host "=== Airflow setup completed ===" -ForegroundColor Green
Write-Host ""
Write-Host "To start Airflow:" -ForegroundColor Cyan
Write-Host "1. Start webserver: airflow webserver --port 8080" -ForegroundColor White
Write-Host "2. Start scheduler (in new terminal): airflow scheduler" -ForegroundColor White
Write-Host "3. Access web UI: http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "To test scraper manually:" -ForegroundColor Cyan
Write-Host "python scraper/direct_iframe_scraper.py" -ForegroundColor White