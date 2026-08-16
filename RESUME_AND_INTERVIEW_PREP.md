# 🎯 Resume Bullet Points & Interview Preparation Guide

This guide provides recruiter-optimized resume bullet points and key technical interview preparation answers for the **E-Commerce Sales Analytics & Data Warehouse Platform** project.

---

## 📄 SECTION 1: Resume Bullet Points (3 Formats)

### Format 1: Comprehensive STAR Bullet (Recommended for Data Engineer / Analytics Engineer roles)
> **E-Commerce Sales Analytics & Cloud Data Warehouse Pipeline** | *Python, SQL, BigQuery, Pandas, Power BI*
> - Engineered an end-to-end data pipeline processing 8,000+ e-commerce transactions using Python (Faker, Pandas) and modeled a Kimball-style Star Schema warehouse in Google BigQuery optimized with date-partitioning and multi-column clustering.
> - Developed robust ETL cleaning workflows handling missing values, corrupted multi-format timestamps, and deduplication, reducing data quality anomalies to 0%.
> - Implemented an automated SQL RFM (Recency, Frequency, Monetary) segmentation model using quintile window functions (`NTILE(5)`), classifying customers into 5 actionable business tiers (Champions, Loyal, At-Risk) and integrated the output into an interactive executive BI dashboard.

---

### Format 2: Concise / High-Impact Bullet (Recommended for Generalist Data Analyst roles)
> **E-Commerce Sales Analytics Platform** | *Python, SQL, BigQuery, Power BI, Docker*
> - Built an end-to-end analytics pipeline extracting, transforming, and loading 8k+ transactions into a Google BigQuery Star Schema warehouse.
> - Wrote advanced SQL CTEs and window functions to compute customer RFM scores, segmenting user base into retention tiers.
> - Designed interactive executive BI dashboards tracking revenue trends, product category velocity, and customer lifetime value.

---

### Format 3: One-Line Summary Bullet (For tight resume space / Project List)
> - **E-Commerce Sales Analytics Platform**: Architected an end-to-end ETL & BigQuery Star Schema data pipeline with SQL-driven RFM customer segmentation and interactive BI dashboards.

---

## 💼 SECTION 2: Top 10 Technical & Behavioral Interview Q&A

### Q1: Can you walk me through the architecture of this project?
**Answer:**
> "The project follows a 5-tier architecture:
> 1. **Data Ingestion/Simulation**: Generates realistic transaction data with seasonal trends and data quality anomalies (nulls, multi-format timestamps, duplicates).
> 2. **ETL & Data Quality Engine**: Uses Pandas to clean, standardize, and transform raw files into structured dimension and fact tables.
> 3. **Data Warehousing**: Modeled as a Kimball Star Schema with a partitioned and clustered `fact_sales` table and `dim_customers`/`dim_products` dimensions in BigQuery/Redshift.
> 4. **Analytics & Segmentation Engine**: Executes SQL queries calculating RFM quintile scores (`NTILE(5)`) to classify customer behavior.
> 5. **BI Presentation**: Surfaces metrics (revenue velocity, retention, category performance) via interactive dashboards."

---

### Q2: Why did you choose a Star Schema over a 3NF (Normalized) or Single Flat Table?
**Answer:**
> "A Star Schema separates measurements into a centralized `fact_sales` table and context into `dim_customers` and `dim_products`. 
> - Compared to 3NF, it reduces the number of complex multi-table joins, maximizing read and aggregation performance for BI queries.
> - Compared to a single flat denormalized table, it prevents massive data redundancy (e.g. repeating customer address or product descriptions across thousands of order rows) and makes dimension updates easier (SCD management)."

---

### Q3: How did you optimize query performance and storage in BigQuery / Redshift?
**Answer:**
> - **In BigQuery**: I partitioned `fact_sales` by `DATE(order_date)`, ensuring queries scanning a specific date range only scan relevant partitions rather than the full table, drastically cutting query cost and latency. I also clustered by `customer_id` and `product_id` for fast customer-level and product-level filtering.
> - **In Redshift**: I applied `DISTSTYLE KEY` on `customer_id` for co-locating data with dimension joins, and defined compound `SORTKEY(order_date, customer_id)` for range scans."

---

### Q4: How does your RFM Segmentation logic work mathematically in SQL?
**Answer:**
> "I computed three core metrics per customer against an anchor analysis date:
> - **Recency**: Days since their last transaction (`DATE_DIFF(max_date, last_order_date, DAY)`).
> - **Frequency**: Total unique orders placed (`COUNT(DISTINCT order_id)`).
> - **Monetary**: Total revenue generated (`SUM(item_total)`).
> 
> Then, using `NTILE(5) OVER (...)`, I assigned quintile scores from 1 to 5. For Recency, the ordering was reversed so the fewest days received a score of 5. Finally, a `CASE` statement classified customers into tiers like **Champions** (555, 455), **Loyal Customers**, **At-Risk**, and **Lost**."

---

### Q5: What real-world data quality issues did you handle in the ETL pipeline?
**Answer:**
> "I simulated and resolved 4 common production issues:
> 1. **Mixed Date Formats & Epochs**: Handled mixed string formats (MM/DD/YYYY, YYYY-MM-DD, Month DD YYYY) and Unix epoch timestamps using custom multi-pass parsing.
> 2. **Duplicate Customer Entries**: Resolved multiple signups using email deduplication and ID normalization.
> 3. **Missing Critical Values**: Handled missing customer emails by fallback imputation or deterministic placeholder mapping.
> 4. **Anomalous Values**: Filtered negative unit prices and zero-quantity items before calculating order totals."

---

### Q6: What is the difference between DirectQuery and Import mode in Power BI when connecting to BigQuery?
**Answer:**
> - **Import Mode**: Downloads a compressed snapshot into Power BI VertiPaq engine in memory. Visuals are super fast, but data is only as fresh as the last scheduled refresh, and file size is capped (1 GB in standard Pro).
> - **DirectQuery Mode**: Sends live SQL queries to BigQuery every time a user interacts with a visual/filter. It supports real-time data and massive petabyte-scale datasets without memory limits, though query latency depends on warehouse performance."

---

### Q7: If order volume grew from 8,000 to 80 million records, how would you scale this pipeline?
**Answer:**
> "I would make three architectural upgrades:
> 1. Replace the single-node Pandas script with **Apache Spark (PySpark)** or **dbt (data build tool)** running directly inside BigQuery/Snowflake.
> 2. Implement an incremental/delta ingestion pattern (e.g. Apache Airflow / Cloud Composer orchestrating micro-batches with watermark timestamps) rather than full reloads.
> 3. Create pre-aggregated materialized views or summary rollup tables for the BI dashboard to avoid scanning 80M raw fact rows on every user click."
