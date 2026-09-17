#!/usr/bin/env python3
"""
Data Exporter for Analytics Dashboard
Extracts aggregated metrics and transactions from the star schema warehouse CSVs
and exports them to `data.json` for static hosting (GitHub Pages, Vercel, Netlify).
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DIRECTORY = PROJECT_ROOT if os.path.exists(os.path.join(PROJECT_ROOT, 'index.html')) else SCRIPT_DIR

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

def ensure_data_exists():
    """Checks if cleaned star schema files exist, otherwise runs generator and ETL."""
    cust_path = os.path.join(DIRECTORY, 'dim_customers.csv')
    prod_path = os.path.join(DIRECTORY, 'dim_products.csv')
    sales_path = os.path.join(DIRECTORY, 'fact_sales.csv')

    if not (os.path.exists(cust_path) and os.path.exists(prod_path) and os.path.exists(sales_path)):
        print("[INFO] Cleaned warehouse CSVs not found. Auto-bootstrapping data...")
        
        # Check raw CSVs
        raw_cust = os.path.join(DIRECTORY, 'customers.csv')
        if not os.path.exists(raw_cust):
            print("[INFO] Generating synthetic e-commerce data...")
            import generate_data
            generate_data.main()
        
        print("[INFO] Running ETL process to build star schema tables...")
        import etl_process
        etl_process.main()

def generate_analytics_payload():
    """Processes warehouse CSVs into a structured JSON payload for the dashboard."""
    import pandas as pd

    customers_path = os.path.join(DIRECTORY, 'dim_customers.csv')
    products_path = os.path.join(DIRECTORY, 'dim_products.csv')
    sales_path = os.path.join(DIRECTORY, 'fact_sales.csv')

    # Load CSVs
    df_cust = pd.read_csv(customers_path)
    df_prod = pd.read_csv(products_path)
    df_sales = pd.read_csv(sales_path)

    # Ensure proper data types
    df_sales['item_total'] = pd.to_numeric(df_sales['item_total'], errors='coerce')
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'], errors='coerce')
    df_cust['signup_date'] = pd.to_datetime(df_cust['signup_date'], errors='coerce')

    # Calculate Core KPI Metrics
    total_revenue = float(df_sales['item_total'].sum())
    total_orders = int(df_sales['order_id'].nunique())
    total_customers = int(df_cust['customer_id'].nunique())
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

    # Sales by Category
    df_joined = df_sales.merge(df_prod, on='product_id', how='inner')
    category_sales = df_joined.groupby('category')['item_total'].sum().round(2).to_dict()

    # Monthly Sales Trend
    df_sales['month'] = df_sales['order_date'].dt.to_period('M').astype(str)
    monthly_sales = df_sales.groupby('month')['item_total'].sum().round(2).sort_index().to_dict()

    # Monthly Signups Trend
    df_cust['month'] = df_cust['signup_date'].dt.to_period('M').astype(str)
    monthly_signups = df_cust.groupby('month').size().sort_index().to_dict()

    # Recent Transactions (Last 10 records)
    recent_df = df_sales.sort_values(by='order_date', ascending=False).head(10)
    recent_joined = recent_df.merge(df_prod, on='product_id', how='left').merge(df_cust, on='customer_id', how='left')
    recent_transactions = []
    for _, row in recent_joined.iterrows():
        recent_transactions.append({
            'order_id': str(row['order_id']),
            'customer_name': str(row['name']) if not pd.isna(row['name']) else 'Unknown',
            'product_name': str(row['product_name']) if not pd.isna(row['product_name']) else 'Unknown Product',
            'category': str(row['category']) if not pd.isna(row['category']) else 'General',
            'quantity': int(row['quantity']) if not pd.isna(row['quantity']) else 1,
            'item_total': float(row['item_total']) if not pd.isna(row['item_total']) else 0.0,
            'order_date': row['order_date'].strftime('%Y-%m-%d %H:%M') if not pd.isna(row['order_date']) else ''
        })

    # Compute RFM Segments dynamically
    max_date = df_sales['order_date'].max()
    last_orders = df_sales.groupby('customer_id')['order_date'].max()
    recency_days = (max_date - last_orders).dt.days
    frequency = df_sales.groupby('customer_id')['order_id'].nunique()
    monetary = df_sales.groupby('customer_id')['item_total'].sum()

    rfm_df = pd.DataFrame({
        'recency': recency_days,
        'frequency': frequency,
        'monetary': monetary
    }).dropna()

    rfm_segments = {}
    if len(rfm_df) >= 5:
        rfm_df['r_score'] = pd.qcut(rfm_df['recency'].rank(method='first', ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm_df['f_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm_df['m_score'] = pd.qcut(rfm_df['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)

        def get_segment(row):
            r, f, m = row['r_score'], row['f_score'], row['m_score']
            if r >= 4 and f >= 4 and m >= 4:
                return 'Champions'
            elif r >= 3 and f >= 3 and m >= 3:
                return 'Loyal Customers'
            elif r >= 4 and f <= 2:
                return 'New / Promising'
            elif r <= 2 and f >= 3:
                return 'At Risk'
            else:
                return 'Lost'

        rfm_df['segment'] = rfm_df.apply(get_segment, axis=1)
        for seg in ['Champions', 'Loyal Customers', 'New / Promising', 'At Risk', 'Lost']:
            sub = rfm_df[rfm_df['segment'] == seg]
            rfm_segments[seg] = {
                'count': int(len(sub)),
                'revenue': round(float(sub['monetary'].sum()), 2)
            }

    payload = {
        'status': 'success',
        'generated_at': str(pd.Timestamp.now()),
        'metrics': {
            'total_revenue': round(total_revenue, 2),
            'total_orders': total_orders,
            'total_customers': total_customers,
            'avg_order_value': round(avg_order_value, 2)
        },
        'category_sales': category_sales,
        'monthly_sales': monthly_sales,
        'monthly_signups': monthly_signups,
        'rfm_segments': rfm_segments,
        'recent_transactions': recent_transactions
    }
    return payload

def main():
    ensure_data_exists()
    payload = generate_analytics_payload()
    output_path = os.path.join(DIRECTORY, 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    print(f"[SUCCESS] Exported analytics data snapshot to: {output_path}")

if __name__ == '__main__':
    main()
