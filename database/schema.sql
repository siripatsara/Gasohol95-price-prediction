-- ===============================================
-- Perfect Gasohol Price Database Schema
-- ===============================================

-- Drop existing tables if they exist
DROP TABLE IF EXISTS daily_gasohol_prices CASCADE;
DROP TABLE IF EXISTS data_quality_logs CASCADE;

-- ===============================================
-- Daily Gasohol Prices Table
-- ===============================================
CREATE TABLE daily_gasohol_prices (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    price_ptt DECIMAL(10,2),
    price_shell DECIMAL(10,2), 
    effective_date VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster date queries
CREATE INDEX idx_gasohol_date ON daily_gasohol_prices(date);

-- ===============================================
-- Data Quality Logs Table
-- ===============================================
CREATE TABLE data_quality_logs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'success', 'error', 'warning'
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster log queries
CREATE INDEX idx_logs_date ON data_quality_logs(date);
CREATE INDEX idx_logs_status ON data_quality_logs(status);

-- ===============================================
-- Load initial data from CSV
-- ===============================================
-- This will be handled by the Python script