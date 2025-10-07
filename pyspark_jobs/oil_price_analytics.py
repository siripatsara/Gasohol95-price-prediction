#!/usr/bin/env python3
"""
Oil Price Analytics PySpark Job
วิเคราะห์ข้อมูลราคาน้ำมันด้วย PySpark สำหรับ SparkSubmitOperator
"""

import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lag, avg, sum, count, when, corr, first, last, 
    date_sub, lit, max, min
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType
)
from pyspark.sql.window import Window
import logging

def create_spark_session():
    """สร้าง Spark Session"""
    return SparkSession.builder \
        .appName("OilPriceAnalytics") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

def read_from_postgresql(spark, postgres_config):
    """อ่านข้อมูลจาก PostgreSQL"""
    return spark.read \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{postgres_config['host']}:5432/{postgres_config['db']}") \
        .option("dbtable", "oil_prices_analytics") \
        .option("user", postgres_config['user']) \
        .option("password", postgres_config['password']) \
        .option("driver", "org.postgresql.Driver") \
        .load()

def perform_oil_price_analytics(df, analysis_date):
    """วิเคราะห์ข้อมูลราคาน้ำมัน"""
    analytics_results = {}
    
    # 1. Price Volatility Analysis
    daily_changes = df.select(
        "date",
        "price_ptt",
        "price_shell", 
        "price_brent",
        lag("price_ptt").over(Window.orderBy("date")).alias("prev_ptt"),
        lag("price_shell").over(Window.orderBy("date")).alias("prev_shell"),
        lag("price_brent").over(Window.orderBy("date")).alias("prev_brent")
    ).withColumn(
        "ptt_change", col("price_ptt") - col("prev_ptt")
    ).withColumn(
        "shell_change", col("price_shell") - col("prev_shell") 
    ).withColumn(
        "brent_change", col("price_brent") - col("prev_brent")
    )
    
    # 2. Moving Averages (7-day, 30-day)
    moving_averages = df.select(
        "date",
        "price_ptt",
        "price_brent",
        avg("price_ptt").over(Window.orderBy("date").rowsBetween(-6, 0)).alias("ptt_7day_avg"),
        avg("price_ptt").over(Window.orderBy("date").rowsBetween(-29, 0)).alias("ptt_30day_avg"),
        avg("price_brent").over(Window.orderBy("date").rowsBetween(-6, 0)).alias("brent_7day_avg"),
        avg("price_brent").over(Window.orderBy("date").rowsBetween(-29, 0)).alias("brent_30day_avg")
    )
    
    # 3. Correlation Analysis
    correlation_matrix = df.select(
        corr("price_ptt", "price_brent").alias("ptt_brent_correlation"),
        corr("price_ptt", "usd_bath").alias("ptt_usd_correlation"),
        corr("price_brent", "usd_bath").alias("brent_usd_correlation")
    ).collect()[0]
    
    # 4. Data Quality Metrics
    quality_metrics = df.select(
        count("*").alias("total_records"),
        sum(when(col("price_ptt").isNull(), 1).otherwise(0)).alias("missing_ptt"),
        sum(when(col("price_brent").isNull(), 1).otherwise(0)).alias("missing_brent"),
        avg("data_quality_score").alias("avg_quality_score"),
        max("data_quality_score").alias("max_quality_score"),
        min("data_quality_score").alias("min_quality_score")
    ).collect()[0]
    
    # 5. Price Trend Classification
    recent_trend = df.filter(col("date") >= date_sub(lit(analysis_date), 7)) \
        .select(
            first("price_ptt").alias("week_start_ptt"),
            last("price_ptt").alias("week_end_ptt"),
            first("price_brent").alias("week_start_brent"),
            last("price_brent").alias("week_end_brent")
        ).collect()[0]
    
    return {
        'daily_changes': daily_changes,
        'moving_averages': moving_averages,
        'correlations': correlation_matrix,
        'quality_metrics': quality_metrics,
        'trend_analysis': recent_trend
    }

def save_analytics_to_postgresql(spark, analytics_results, postgres_config, analysis_date):
    """บันทึกผลการวิเคราะห์กลับไป PostgreSQL"""
    
    # Create analytics summary DataFrame
    summary_data = [
        (
            analysis_date,
            float(analytics_results['correlations']['ptt_brent_correlation']),
            float(analytics_results['correlations']['ptt_usd_correlation']),
            float(analytics_results['correlations']['brent_usd_correlation']),
            int(analytics_results['quality_metrics']['total_records']),
            int(analytics_results['quality_metrics']['missing_ptt']),
            int(analytics_results['quality_metrics']['missing_brent']),
            float(analytics_results['quality_metrics']['avg_quality_score']),
            float(analytics_results['trend_analysis']['week_end_ptt'] - analytics_results['trend_analysis']['week_start_ptt']),
            float(analytics_results['trend_analysis']['week_end_brent'] - analytics_results['trend_analysis']['week_start_brent'])
        )
    ]
    
    schema = StructType([
        StructField("analysis_date", StringType(), True),
        StructField("ptt_brent_correlation", DoubleType(), True),
        StructField("ptt_usd_correlation", DoubleType(), True),
        StructField("brent_usd_correlation", DoubleType(), True),
        StructField("total_records", IntegerType(), True),
        StructField("missing_ptt_count", IntegerType(), True),
        StructField("missing_brent_count", IntegerType(), True),
        StructField("avg_quality_score", DoubleType(), True),
        StructField("ptt_week_change", DoubleType(), True),
        StructField("brent_week_change", DoubleType(), True)
    ])
    
    summary_df = spark.createDataFrame(summary_data, schema)
    
    # Write to PostgreSQL analytics summary table
    summary_df.write \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{postgres_config['host']}:5432/{postgres_config['db']}") \
        .option("dbtable", "oil_analytics_summary") \
        .option("user", postgres_config['user']) \
        .option("password", postgres_config['password']) \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

def main():
    parser = argparse.ArgumentParser(description='Oil Price Analytics PySpark Job')
    parser.add_argument('--postgres_host', required=True, help='PostgreSQL host')
    parser.add_argument('--postgres_db', required=True, help='PostgreSQL database')
    parser.add_argument('--postgres_user', required=True, help='PostgreSQL user')
    parser.add_argument('--postgres_password', required=True, help='PostgreSQL password')
    parser.add_argument('--analysis_date', required=True, help='Analysis date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Create Spark session
        spark = create_spark_session()
        logger.info("Spark session created successfully")
        
        # PostgreSQL configuration
        postgres_config = {
            'host': args.postgres_host,
            'db': args.postgres_db,
            'user': args.postgres_user,
            'password': args.postgres_password
        }
        
        # Read data from PostgreSQL
        logger.info("Reading data from PostgreSQL...")
        df = read_from_postgresql(spark, postgres_config)
        
        logger.info(f"Loaded {df.count()} records from PostgreSQL")
        
        # Perform analytics
        logger.info("Performing oil price analytics...")
        analytics_results = perform_oil_price_analytics(df, args.analysis_date)
        
        # Save results back to PostgreSQL
        logger.info("Saving analytics results to PostgreSQL...")
        save_analytics_to_postgresql(spark, analytics_results, postgres_config, args.analysis_date)
        
        # Log summary statistics
        logger.info("=== ANALYTICS SUMMARY ===")
        logger.info(f"Analysis Date: {args.analysis_date}")
        logger.info(f"Total Records Analyzed: {analytics_results['quality_metrics']['total_records']}")
        logger.info(f"Average Data Quality Score: {analytics_results['quality_metrics']['avg_quality_score']:.3f}")
        logger.info(f"PTT-Brent Correlation: {analytics_results['correlations']['ptt_brent_correlation']:.3f}")
        logger.info(f"PTT-USD Correlation: {analytics_results['correlations']['ptt_usd_correlation']:.3f}")
        
        logger.info("Oil price analytics completed successfully!")
        
    except Exception as e:
        logger.error(f"Analytics job failed: {str(e)}")
        raise
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()