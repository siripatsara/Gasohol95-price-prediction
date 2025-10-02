#!/bin/bash
# setup_airflow.sh
# สคริปต์สำหรับตั้งค่า Airflow สำหรับ EPPO oil price scraping

echo "=== Setting up Airflow for EPPO Oil Price Scraping ==="

# สร้าง directories ที่จำเป็น
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p plugins
mkdir -p data
mkdir -p backups

# Copy scraper ไปยัง dags directory
echo "Setting up scraper in dags directory..."
cp -r scraper dags/

# Copy data file
echo "Setting up data file..."
cp data/only_2_stations.csv data/

# Set environment variables
export AIRFLOW_HOME=$(pwd)
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOGS_FOLDER=$(pwd)/logs
export AIRFLOW__CORE__PLUGINS_FOLDER=$(pwd)/plugins

echo "AIRFLOW_HOME set to: $AIRFLOW_HOME"

# Initialize Airflow database (if not exists)
if [ ! -f "airflow.db" ]; then
    echo "Initializing Airflow database..."
    airflow db init
fi

# Create admin user (if not exists)
echo "Creating admin user..."
airflow users create \
    --username admin \
    --firstname EPPO \
    --lastname Admin \
    --role Admin \
    --email admin@eppo.local \
    --password admin123 || echo "User already exists"

echo "=== Airflow setup completed ==="
echo ""
echo "To start Airflow:"
echo "1. Start webserver: airflow webserver --port 8080"
echo "2. Start scheduler: airflow scheduler"
echo "3. Access web UI: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "To test DAG manually:"
echo "airflow dags test eppo_oil_price_scraper $(date -I)"