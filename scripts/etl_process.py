import csv
import datetime
import os
import sys

# Attempt to import pandas, install if missing
try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("The 'pandas' or 'numpy' library is not installed.")
    print("Attempting to install 'pandas' and 'numpy' using pip...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "numpy"])
        import pandas as pd
        import numpy as np
        print("Libraries successfully installed!")
    except Exception as e:
        print(f"Failed to install required libraries automatically: {e}")
        print("Please run 'pip install pandas numpy' manually and run this script again.")
        sys.exit(1)

def parse_dates(series):
    """Robust date parser that handles mixed formats and Unix timestamps."""
    def convert_val(val):
        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() in ("nan", "none", "null"):
            return pd.NaT
        val_str = str(val).strip()
        
        # Check if Unix timestamp (string of digits only)
        if val_str.isdigit():
            try:
                return pd.to_datetime(int(val_str), unit='s')
            except Exception:
                return pd.NaT
                
        # Try standard parsing with mixed format support (Pandas 2.0+)
        try:
            return pd.to_datetime(val_str, format='mixed')
        except Exception:
            try:
                return pd.to_datetime(val_str)
            except Exception:
                return pd.NaT
                
    return pd.to_datetime(series.apply(convert_val), errors='coerce')

def main():
    # Define file paths (support running from root or scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    base_dir = project_root if os.path.exists(os.path.join(project_root, 'index.html')) else script_dir

    customers_path = os.path.join(base_dir, 'customers.csv')
    products_path = os.path.join(base_dir, 'products.csv')
    orders_path = os.path.join(base_dir, 'orders.csv')

    # Output paths (Star Schema)
    dim_customers_path = os.path.join(base_dir, 'dim_customers.csv')
    dim_products_path = os.path.join(base_dir, 'dim_products.csv')
    fact_sales_path = os.path.join(base_dir, 'fact_sales.csv')

    # Check if input files exist
    for path in [customers_path, products_path, orders_path]:
        if not os.path.exists(path):
            print(f"Error: Required file not found at {path}")
            print("Please run 'python scripts/generate_data.py' first to generate the raw datasets.")
            sys.exit(1)

    print("=" * 60)
    print("STARTING ETL PROCESS FOR STAR SCHEMA WAREHOUSE")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. EXTRACT DATA
    # -------------------------------------------------------------
    print("\n--- STEP 1: EXTRACTING DATA ---")
    df_cust = pd.read_csv(customers_path)
    df_prod = pd.read_csv(products_path)
    df_ord = pd.read_csv(orders_path)

    cust_initial_rows = len(df_cust)
    prod_initial_rows = len(df_prod)
    ord_initial_rows = len(df_ord)

    print(f"Loaded customers.csv : {cust_initial_rows} rows")
    print(f"Loaded products.csv  : {prod_initial_rows} rows")
    print(f"Loaded orders.csv    : {ord_initial_rows} rows")

    # -------------------------------------------------------------
    # 2. CLEAN & TRANSFORM CUSTOMERS
    # -------------------------------------------------------------
    print("\n--- STEP 2: CLEANING CUSTOMERS ---")
    
    # Track metrics
    cust_clean_summary = {}

    # Duplicate removal
    # A. Exact row duplicates
    exact_duplicates = df_cust.duplicated().sum()
    df_cust = df_cust.drop_duplicates()
    cust_clean_summary['Exact Row Duplicates Removed'] = exact_duplicates

    # B. CRM Profile duplicates (Same email address, keeping first signup)
    # Filter out null emails first so we don't drop multiple nulls under duplicate logic
    non_null_emails = df_cust['email'].notna() & (df_cust['email'] != "") & (df_cust['email'] != "NaN")
    crm_duplicates = df_cust[non_null_emails].duplicated(subset=['email'], keep='first').sum()
    df_cust = pd.concat([
        df_cust[~non_null_emails],
        df_cust[non_null_emails].drop_duplicates(subset=['email'], keep='first')
    ])
    cust_clean_summary['CRM Profile Duplicates (Same Email) Removed'] = crm_duplicates

    # Handle missing emails
    missing_email_mask = df_cust['email'].isna() | (df_cust['email'].astype(str).str.strip() == "") | (df_cust['email'].astype(str).str.strip().str.lower() == "nan")
    missing_emails_count = missing_email_mask.sum()
    df_cust = df_cust[~missing_email_mask]
    cust_clean_summary['Rows with Missing Emails Dropped'] = missing_emails_count

    # Standardize signup dates
    original_dates = df_cust['signup_date'].copy()
    parsed_dates = parse_dates(df_cust['signup_date'])
    
    # Count format changes (where string format didn't match YYYY-MM-DD)
    date_is_standard = original_dates.astype(str).str.match(r'^\d{4}-\d{2}-\d{2}$')
    format_standardized = (~date_is_standard).sum()
    
    # Check for unparseable dates
    unparseable_dates = parsed_dates.isna().sum()
    
    # Update DataFrame
    df_cust['signup_date'] = parsed_dates
    # Drop any row with unparseable signup date
    df_cust = df_cust.dropna(subset=['signup_date'])
    
    # Format dates as standard YYYY-MM-DD
    df_cust['signup_date'] = df_cust['signup_date'].dt.strftime('%Y-%m-%d')
    
    cust_clean_summary['Dates Standardized to YYYY-MM-DD'] = format_standardized
    cust_clean_summary['Unparseable Signup Dates Dropped'] = unparseable_dates

    # -------------------------------------------------------------
    # 3. CLEAN & TRANSFORM PRODUCTS
    # -------------------------------------------------------------
    print("\n--- STEP 3: CLEANING PRODUCTS ---")
    prod_clean_summary = {}
    
    # Cast prices to float and remove duplicates if any
    exact_prod_duplicates = df_prod.duplicated().sum()
    df_prod = df_prod.drop_duplicates()
    df_prod['price'] = pd.to_numeric(df_prod['price'], errors='coerce')
    
    prod_clean_summary['Duplicates Removed'] = exact_prod_duplicates

    # -------------------------------------------------------------
    # 4. CLEAN & TRANSFORM ORDERS
    # -------------------------------------------------------------
    print("\n--- STEP 4: CLEANING ORDERS & CALCULATING TOTALS ---")
    ord_clean_summary = {}

    # Exact duplicate orders
    exact_ord_duplicates = df_ord.duplicated().sum()
    df_ord = df_ord.drop_duplicates()
    ord_clean_summary['Exact Row Duplicates Removed'] = exact_ord_duplicates

    # Standardize order dates
    original_order_dates = df_ord['order_date'].copy()
    parsed_order_dates = parse_dates(df_ord['order_date'])
    
    # Check format changes (standard format is YYYY-MM-DD HH:MM:SS)
    order_date_is_standard = original_order_dates.astype(str).str.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
    ord_format_standardized = (~order_date_is_standard).sum()
    
    unparseable_order_dates = parsed_order_dates.isna().sum()
    df_ord['order_date'] = parsed_order_dates
    df_ord = df_ord.dropna(subset=['order_date'])
    ord_clean_summary['Dates Standardized to YYYY-MM-DD HH:MM:SS'] = ord_format_standardized
    ord_clean_summary['Unparseable Order Dates Dropped'] = unparseable_order_dates

    # Clean quantities and prices
    df_ord['quantity'] = pd.to_numeric(df_ord['quantity'], errors='coerce')
    df_ord['unit_price'] = pd.to_numeric(df_ord['unit_price'], errors='coerce')

    # Remove invalid order amounts (quantity <= 0 or unit_price <= 0)
    invalid_qty_mask = (df_ord['quantity'] <= 0) | df_ord['quantity'].isna()
    invalid_price_mask = (df_ord['unit_price'] <= 0) | df_ord['unit_price'].isna()
    
    invalid_rows_count = (invalid_qty_mask | invalid_price_mask).sum()
    df_ord = df_ord[~(invalid_qty_mask | invalid_price_mask)]
    
    ord_clean_summary['Invalid Amounts (Qty <= 0 or Price <= 0) Dropped'] = invalid_rows_count

    # Calculate item_total and order_total
    df_ord['item_total'] = df_ord['quantity'] * df_ord['unit_price']
    
    # Group by order_id to calculate order_total for each order
    order_totals = df_ord.groupby('order_id')['item_total'].transform('sum')
    df_ord['order_total'] = order_totals.round(2)
    df_ord['item_total'] = df_ord['item_total'].round(2)

    # -------------------------------------------------------------
    # 5. REFERENTIAL INTEGRITY (STAR SCHEMA TRANSFORMATION)
    # -------------------------------------------------------------
    print("\n--- STEP 5: TRANSFORMING FOR STAR SCHEMA & ENFORCING INTEGRITY ---")
    
    # Filter fact_sales to only contain active customers and products
    valid_customers = set(df_cust['customer_id'])
    valid_products = set(df_prod['product_id'])
    
    orphan_customer_orders = (~df_ord['customer_id'].isin(valid_customers)).sum()
    orphan_product_orders = (~df_ord['product_id'].isin(valid_products)).sum()
    
    df_ord = df_ord[df_ord['customer_id'].isin(valid_customers)]
    df_ord = df_ord[df_ord['product_id'].isin(valid_products)]
    
    ord_clean_summary['Orphan Customer Records Dropped'] = orphan_customer_orders
    ord_clean_summary['Orphan Product Records Dropped'] = orphan_product_orders

    # Format order dates back to string format
    df_ord['order_date'] = df_ord['order_date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Save to Star Schema CSV files
    # Dimension Tables
    df_cust.to_csv(dim_customers_path, index=False)
    df_prod.to_csv(dim_products_path, index=False)
    # Fact Table
    df_ord.to_csv(fact_sales_path, index=False)

    # -------------------------------------------------------------
    # PRINT ETL CLEANING SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("ETL JOB SUMMARY & CLEANING STATS")
    print("=" * 60)
    
    print("\n1. CUSTOMERS DIMENSION (dim_customers):")
    print(f"   Initial rows extracted   : {cust_initial_rows}")
    for metric, count in cust_clean_summary.items():
        print(f"   - {metric:<40}: {count}")
    print(f"   Final rows loaded        : {len(df_cust)}")

    print("\n2. PRODUCTS DIMENSION (dim_products):")
    print(f"   Initial rows extracted   : {prod_initial_rows}")
    for metric, count in prod_clean_summary.items():
        print(f"   - {metric:<40}: {count}")
    print(f"   Final rows loaded        : {len(df_prod)}")

    print("\n3. SALES FACT TABLE (fact_sales):")
    print(f"   Initial rows extracted   : {ord_initial_rows}")
    for metric, count in ord_clean_summary.items():
        print(f"   - {metric:<40}: {count}")
    print(f"   Final rows loaded        : {len(df_ord)}")
    print("=" * 60)
    print("Star schema files generated successfully:")
    print(f"  - Dimension Customers: {dim_customers_path}")
    print(f"  - Dimension Products:  {dim_products_path}")
    print(f"  - Fact Sales:          {fact_sales_path}")
    print("=" * 60)

if __name__ == '__main__':
    main()
