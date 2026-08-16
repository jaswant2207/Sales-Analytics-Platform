-- =============================================================================
-- RFM (Recency, Frequency, Monetary) ANALYSIS QUERY FOR BIGQUERY & REDSHIFT
-- =============================================================================
-- Calculates RFM metrics and quintile scores (1 to 5) for every customer.
-- 
-- Definitions:
--   - Recency  : Days between reference date (latest order in DB) and customer's last order.
--                R_Score 5 = Most Recent (Best), 1 = Least Recent.
--   - Frequency: Total number of unique orders placed by the customer.
--                F_Score 5 = Highest Frequency (Best), 1 = Lowest Frequency.
--   - Monetary : Total amount spent by the customer.
--                M_Score 5 = Highest Spend (Best), 1 = Lowest Spend.
-- =============================================================================

WITH reference_date AS (
    -- Get the maximum order date across the entire warehouse as the snapshot/analysis date
    SELECT MAX(CAST(order_date AS DATE)) AS max_analysis_date
    FROM fact_sales
),

customer_rfm_metrics AS (
    -- Calculate raw Recency (days), Frequency (order count), and Monetary (total spend)
    SELECT 
        c.customer_id,
        c.name AS customer_name,
        c.email,
        -- Recency: Days between reference date and latest order date for this customer
        DATE_DIFF(ref.max_analysis_date, MAX(CAST(f.order_date AS DATE)), DAY) AS recency_days,
        -- Frequency: Count of distinct order IDs
        COUNT(DISTINCT f.order_id) AS frequency_orders,
        -- Monetary: Total spend across all line items
        ROUND(CAST(SUM(f.item_total) AS NUMERIC), 2) AS monetary_spend
    FROM dim_customers c
    JOIN fact_sales f ON c.customer_id = f.customer_id
    CROSS JOIN reference_date ref
    GROUP BY c.customer_id, c.name, c.email, ref.max_analysis_date
),

customer_rfm_scores AS (
    -- Assign quintile scores (1 to 5) using NTILE(5)
    SELECT 
        customer_id,
        customer_name,
        email,
        recency_days,
        frequency_orders,
        monetary_spend,
        
        -- Recency Score: Inverse ranking so fewest days gets score 5 (best)
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        
        -- Frequency Score: Higher frequency gets score 5 (best)
        NTILE(5) OVER (ORDER BY frequency_orders ASC) AS f_score,
        
        -- Monetary Score: Higher spend gets score 5 (best)
        NTILE(5) OVER (ORDER BY monetary_spend ASC) AS m_score
    FROM customer_rfm_metrics
)

SELECT 
    customer_id,
    customer_name,
    email,
    recency_days,
    frequency_orders,
    monetary_spend,
    r_score,
    f_score,
    m_score,
    -- Combined RFM Cell String (e.g. '555' for Champions, '111' for Lost Customers)
    CONCAT(CAST(r_score AS STRING), CAST(f_score AS STRING), CAST(m_score AS STRING)) AS rfm_cell,
    -- Customer Segmentation Category
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising / New Customers'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk / Need Attention'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost Customers'
        ELSE 'Potential / Hibernating'
    END AS customer_segmentation
FROM customer_rfm_scores
ORDER BY monetary_spend DESC;
