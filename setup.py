#!/usr/bin/env python3
"""
Setup script for Perfect Oil Price Scraping project
สคริปต์สำหรับตั้งค่าโครงการ scraping ราคาน้ำมัน
"""

import os
import sys
import subprocess
import time
import psycopg2
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectSetup:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_config = {
            'host': 'localhost',
            'port': 5435,
            'database': 'gasohol_prediction',
            'user': 'postgres',
            'password': 'postgres123'
        }

    def install_requirements(self):
        """ติดตั้ง Python packages"""
        try:
            logger.info("Installing Python requirements...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 
                os.path.join(self.project_dir, 'requirements.txt')
            ], check=True)
            logger.info("✅ Requirements installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install requirements: {e}")
            return False

    def start_docker_services(self):
        """เริ่ม Docker services"""
        try:
            logger.info("Starting Docker services...")
            os.chdir(self.project_dir)
            
            # Start basic services first
            subprocess.run([
                'docker-compose', 'up', '-d', 
                'postgres', 'pgadmin', 'redis'
            ], check=True)
            
            logger.info("Waiting for PostgreSQL to be ready...")
            time.sleep(30)
            
            logger.info("✅ Docker services started successfully!")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start Docker services: {e}")
            return False

    def test_database_connection(self):
        """ทดสอบการเชื่อมต่อฐานข้อมูล"""
        try:
            logger.info("Testing database connection...")
            
            # Wait for database to be ready
            max_retries = 10
            for i in range(max_retries):
                try:
                    conn = psycopg2.connect(**self.db_config)
                    conn.close()
                    logger.info("✅ Database connection successful!")
                    return True
                except psycopg2.OperationalError:
                    if i < max_retries - 1:
                        logger.info(f"Database not ready, retrying in 5 seconds... ({i+1}/{max_retries})")
                        time.sleep(5)
                    else:
                        raise
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    def load_initial_data(self):
        """โหลดข้อมูลเริ่มต้นจาก CSV"""
        try:
            logger.info("Loading initial data from CSV...")
            
            # Import and run CSV loader
            sys.path.append(os.path.join(self.project_dir, 'scripts'))
            from load_csv_data import CSVLoader
            
            loader = CSVLoader()
            success = loader.load_csv_to_database(
                os.path.join(self.project_dir, 'data', 'only_2_stations.csv')
            )
            
            if success:
                logger.info("✅ Initial data loaded successfully!")
                return True
            else:
                logger.error("❌ Failed to load initial data!")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error loading initial data: {e}")
            return False

    def test_scraper(self):
        """ทดสอบ scraper"""
        try:
            logger.info("Testing oil price scraper...")
            
            # Import and test scraper
            sys.path.append(os.path.join(self.project_dir, 'scraper'))
            from eppo_oil_scraper import EPPOOilScraper
            
            scraper = EPPOOilScraper()
            
            # Test web scraping only (not full process to avoid duplicate data)
            scraped_data = scraper.scrape_oil_prices()
            
            if scraped_data:
                logger.info("✅ Scraper test successful!")
                logger.info(f"   Sample data: PTT={scraped_data['price_ptt']}, Shell={scraped_data['price_shell']}")
                return True
            else:
                logger.error("❌ Scraper test failed!")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing scraper: {e}")
            return False

    def start_airflow(self):
        """เริ่ม Airflow services"""
        try:
            logger.info("Starting Airflow services...")
            os.chdir(self.project_dir)
            
            subprocess.run([
                'docker-compose', '-f', 'docker-compose-airflow.yml', 
                'up', '-d'
            ], check=True)
            
            logger.info("Airflow is starting up...")
            logger.info("✅ Airflow services started!")
            logger.info("   Airflow UI will be available at: http://localhost:8083")
            logger.info("   Username: admin, Password: admin123")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start Airflow: {e}")
            return False

    def display_summary(self):
        """แสดงสรุปการตั้งค่า"""
        print("\n" + "="*60)
        print("🎉 PERFECT OIL PRICE SCRAPING SETUP COMPLETED!")
        print("="*60)
        print("\n📊 Services:")
        print("   • PostgreSQL Database: localhost:5435")
        print("   • pgAdmin: http://localhost:5051 (admin@gasohol.com / admin123)")
        print("   • Airflow UI: http://localhost:8083 (admin / admin123)")
        print("   • Redis: localhost:6380")
        
        print("\n📁 Project Structure:")
        print("   • Scraper: ./scraper/eppo_oil_scraper.py")
        print("   • Database Schema: ./database/schema.sql")
        print("   • Data: ./data/only_2_stations.csv")
        print("   • Airflow DAGs: ./dags/")
        
        print("\n🚀 Next Steps:")
        print("   1. Access Airflow UI at http://localhost:8083")
        print("   2. Enable the 'eppo_oil_price_scraper' DAG")
        print("   3. The scraper will run automatically at 6 AM, 12 PM, and 6 PM daily")
        print("   4. Monitor logs and data quality in pgAdmin")
        
        print("\n🛠 Manual Commands:")
        print("   • Test scraper: python test_scraper.py")
        print("   • Load CSV data: python scripts/load_csv_data.py")
        print("   • View logs: docker logs perfect_airflow_scheduler")
        
        print("\n" + "="*60)

    def run_setup(self):
        """รันการตั้งค่าทั้งหมด"""
        logger.info("🚀 Starting Perfect Oil Price Scraping Project Setup...")
        
        steps = [
            ("Installing requirements", self.install_requirements),
            ("Starting Docker services", self.start_docker_services),
            ("Testing database connection", self.test_database_connection),
            ("Loading initial data", self.load_initial_data),
            ("Testing scraper", self.test_scraper),
            ("Starting Airflow", self.start_airflow)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 Step: {step_name}")
            if not step_func():
                logger.error(f"❌ Setup failed at step: {step_name}")
                return False
        
        self.display_summary()
        return True

def main():
    """Main function"""
    setup = ProjectSetup()
    
    try:
        success = setup.run_setup()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()