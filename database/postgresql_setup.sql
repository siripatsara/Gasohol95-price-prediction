-- ============================================================================
-- PostgreSQL Schema Setup for Oil Price Analytics
-- รองรับ Smart Oil Scraper + Airflow + PySpark Analytics
-- ============================================================================

-- สร้าง schema สำหรับ oil analytics
CREATE SCHEMA IF NOT EXISTS oil_analytics;

-- ============================================================================
-- 1. ตาราง oil_prices_analytics - ข้อมูลหลักจาก Smart Scraper
-- ============================================================================
CREATE TABLE IF NOT EXISTS oil_analytics.oil_prices_analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    price_ptt DECIMAL(10,2),
    price_shell DECIMAL(10,2),
    effective_date VARCHAR(50),
    price_brent DECIMAL(10,2),
    usd_bath DECIMAL(10,4),
    price_levy DECIMAL(10,2),
    scraping_mode VARCHAR(20), -- 'full_scraping', 'smart_detection', 'manual_execution'
    execution_time TIMESTAMP,
    data_quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, scraping_mode)
);

-- Indexes สำหรับ performance
CREATE INDEX IF NOT EXISTS idx_oil_prices_date ON oil_analytics.oil_prices_analytics(date);
CREATE INDEX IF NOT EXISTS idx_oil_prices_mode ON oil_analytics.oil_prices_analytics(scraping_mode);
CREATE INDEX IF NOT EXISTS idx_oil_prices_execution_time ON oil_analytics.oil_prices_analytics(execution_time);
CREATE INDEX IF NOT EXISTS idx_oil_prices_quality ON oil_analytics.oil_prices_analytics(data_quality_score);

-- ============================================================================
-- 2. ตาราง oil_analytics_summary - ผลลัพธ์จาก PySpark Analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS oil_analytics.oil_analytics_summary (
    id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    ptt_brent_correlation DECIMAL(8,6),
    ptt_usd_correlation DECIMAL(8,6),
    brent_usd_correlation DECIMAL(8,6),
    total_records INTEGER,
    missing_ptt_count INTEGER,
    missing_brent_count INTEGER,
    avg_quality_score DECIMAL(3,2),
    ptt_week_change DECIMAL(10,4),
    brent_week_change DECIMAL(10,4),
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(analysis_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_analytics_summary_date ON oil_analytics.oil_analytics_summary(analysis_date);
CREATE INDEX IF NOT EXISTS idx_analytics_summary_correlation ON oil_analytics.oil_analytics_summary(ptt_brent_correlation);

-- ============================================================================
-- 3. ตาราง airflow_execution_log - Log การทำงานของ Airflow DAG
-- ============================================================================
CREATE TABLE IF NOT EXISTS oil_analytics.airflow_execution_log (
    id SERIAL PRIMARY KEY,
    dag_id VARCHAR(100) NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    execution_date TIMESTAMP NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20), -- 'success', 'failed', 'running', 'skipped'
    log_message TEXT,
    xcom_data JSONB, -- เก็บ XCom data เป็น JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_airflow_log_dag_task ON oil_analytics.airflow_execution_log(dag_id, task_id);
CREATE INDEX IF NOT EXISTS idx_airflow_log_execution_date ON oil_analytics.airflow_execution_log(execution_date);
CREATE INDEX IF NOT EXISTS idx_airflow_log_status ON oil_analytics.airflow_execution_log(status);

-- ============================================================================
-- 4. ตาราง data_quality_monitoring - Monitor คุณภาพข้อมูล
-- ============================================================================
CREATE TABLE IF NOT EXISTS oil_analytics.data_quality_monitoring (
    id SERIAL PRIMARY KEY,
    check_date DATE NOT NULL,
    source_name VARCHAR(50), -- 'eppo', 'fred', 'bot', 'levy'
    total_records INTEGER,
    null_count INTEGER,
    duplicate_count INTEGER,
    outlier_count INTEGER,
    quality_score DECIMAL(3,2),
    quality_issues TEXT[], -- Array ของปัญหาที่พบ
    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_quality_monitoring_date ON oil_analytics.data_quality_monitoring(check_date);
CREATE INDEX IF NOT EXISTS idx_quality_monitoring_source ON oil_analytics.data_quality_monitoring(source_name);

-- ============================================================================
-- 5. Views สำหรับ Analytics Dashboard
-- ============================================================================

-- View: ข้อมูลราคาล่าสุด 30 วัน
CREATE OR REPLACE VIEW oil_analytics.latest_prices_30days AS
SELECT 
    date,
    price_ptt,
    price_shell,
    price_brent,
    usd_bath,
    price_levy,
    scraping_mode,
    data_quality_score
FROM oil_analytics.oil_prices_analytics 
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;

-- View: สรุปคุณภาพข้อมูลรายสัปดาห์
CREATE OR REPLACE VIEW oil_analytics.weekly_quality_summary AS
SELECT 
    DATE_TRUNC('week', check_date) as week_start,
    source_name,
    AVG(quality_score) as avg_quality_score,
    SUM(null_count) as total_nulls,
    SUM(duplicate_count) as total_duplicates,
    COUNT(*) as total_checks
FROM oil_analytics.data_quality_monitoring
WHERE check_date >= CURRENT_DATE - INTERVAL '4 weeks'
GROUP BY DATE_TRUNC('week', check_date), source_name
ORDER BY week_start DESC, source_name;

-- View: Correlation trends
CREATE OR REPLACE VIEW oil_analytics.correlation_trends AS
SELECT 
    analysis_date,
    ptt_brent_correlation,
    ptt_usd_correlation,
    brent_usd_correlation,
    LAG(ptt_brent_correlation) OVER (ORDER BY analysis_date) as prev_ptt_brent_corr,
    LAG(ptt_usd_correlation) OVER (ORDER BY analysis_date) as prev_ptt_usd_corr
FROM oil_analytics.oil_analytics_summary
WHERE analysis_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY analysis_date;

-- ============================================================================
-- 6. Functions สำหรับ Data Quality Checking
-- ============================================================================

-- Function: คำนวณ data quality score
CREATE OR REPLACE FUNCTION oil_analytics.calculate_quality_score(
    total_records INTEGER,
    null_count INTEGER,
    duplicate_count INTEGER,
    outlier_count INTEGER
) RETURNS DECIMAL(3,2) AS $$
DECLARE
    score DECIMAL(3,2);
BEGIN
    -- Base score 1.0, ลดตามปัญหาที่พบ
    score := 1.0;
    
    -- ลดคะแนนตาม null values (สูงสุด -0.3)
    score := score - LEAST(0.3, (null_count::DECIMAL / total_records) * 0.5);
    
    -- ลดคะแนนตาม duplicates (สูงสุด -0.2)
    score := score - LEAST(0.2, (duplicate_count::DECIMAL / total_records) * 0.4);
    
    -- ลดคะแนนตาม outliers (สูงสุด -0.1)
    score := score - LEAST(0.1, (outlier_count::DECIMAL / total_records) * 0.2);
    
    -- ขั้นต่ำ 0.0
    score := GREATEST(0.0, score);
    
    RETURN score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. Sample Data & Test Queries
-- ============================================================================

-- Insert sample data quality monitoring
INSERT INTO oil_analytics.data_quality_monitoring 
(check_date, source_name, total_records, null_count, duplicate_count, outlier_count, quality_score, quality_issues)
VALUES 
    (CURRENT_DATE, 'eppo', 100, 2, 0, 1, 0.95, ARRAY['minor_nulls']),
    (CURRENT_DATE, 'fred', 100, 0, 1, 0, 0.98, ARRAY['single_duplicate']),
    (CURRENT_DATE, 'bot', 100, 1, 0, 2, 0.93, ARRAY['minor_nulls', 'outliers']),
    (CURRENT_DATE, 'levy', 100, 0, 0, 0, 1.00, ARRAY[]::TEXT[])
ON CONFLICT DO NOTHING;

-- Test query: Check data quality trends
SELECT 
    source_name,
    AVG(quality_score) as avg_quality,
    COUNT(*) as total_checks,
    MIN(quality_score) as min_quality,
    MAX(quality_score) as max_quality
FROM oil_analytics.data_quality_monitoring 
WHERE check_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY source_name
ORDER BY avg_quality DESC;

-- ============================================================================
-- 8. Triggers สำหรับ Auto-update timestamps
-- ============================================================================

-- Function สำหรับ update timestamp
CREATE OR REPLACE FUNCTION oil_analytics.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger สำหรับ oil_prices_analytics
CREATE TRIGGER update_oil_prices_updated_at
    BEFORE UPDATE ON oil_analytics.oil_prices_analytics
    FOR EACH ROW EXECUTE FUNCTION oil_analytics.update_updated_at_column();

-- ============================================================================
-- 9. Permissions & Security
-- ============================================================================

-- Grant permissions สำหรับ airflow user
GRANT USAGE ON SCHEMA oil_analytics TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA oil_analytics TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA oil_analytics TO airflow;

-- Grant select สำหรับ read-only users (dashboard)
-- GRANT SELECT ON ALL TABLES IN SCHEMA oil_analytics TO readonly_user;

-- ============================================================================
-- 10. Maintenance & Cleanup Jobs
-- ============================================================================

-- Function: Cleanup old logs (เก็บแค่ 90 วัน)
CREATE OR REPLACE FUNCTION oil_analytics.cleanup_old_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM oil_analytics.airflow_execution_log 
    WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- คำแนะนำ: ตั้ง Cron job รัน cleanup_old_logs() ทุกสัปดาห์

COMMIT;