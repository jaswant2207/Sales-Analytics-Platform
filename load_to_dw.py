import os
import sys

# -------------------------------------------------------------
# CONFIGURATION & SETTINGS
# -------------------------------------------------------------
# Change this to 'bigquery' or 'redshift' depending on your warehouse.
DW_TYPE = os.getenv('DW_TYPE', 'bigquery').lower()

# BigQuery Settings
BQ_PROJECT_ID = os.getenv('BQ_PROJECT_ID', 'your-gcp-project')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'ecommerce_warehouse')

# AWS Redshift & S3 Settings
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'your-s3-bucket-name')
REDSHIFT_CLUSTER_ID = os.getenv('REDSHIFT_CLUSTER_ID', 'your-redshift-cluster')
REDSHIFT_DATABASE = os.getenv('REDSHIFT_DATABASE', 'dev')
REDSHIFT_DB_USER = os.getenv('REDSHIFT_DB_USER', 'awsuser')
REDSHIFT_IAM_ROLE_ARN = os.getenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::123456789012:role/RedshiftCopyRole')


# -------------------------------------------------------------
# DEPENDENCY CHECKER
# -------------------------------------------------------------
required_packages = []
if DW_TYPE == 'bigquery':
    required_packages = ['google-cloud-bigquery', 'pandas']
elif DW_TYPE == 'redshift':
    required_packages = ['boto3']

missing_packages = []
for pkg in required_packages:
    try:
        __import__(pkg.replace('-', '_'))
    except ImportError:
        missing_packages.append(pkg)

if missing_packages:
    print(f"Missing required packages for {DW_TYPE}: {missing_packages}")
    print(f"Attempting to install missing packages using pip...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
        print("Libraries successfully installed!")
    except Exception as e:
        print(f"Failed to install required libraries automatically: {e}")
        print(f"Please run 'pip install {' '.join(missing_packages)}' manually and run this script again.")
        sys.exit(1)


# -------------------------------------------------------------
# BIGQUERY LOADING IMPLEMENTATION
# -------------------------------------------------------------
def load_to_bigquery(client, dataset_id, table_id, local_csv_path, primary_keys):
    """Loads CSV to a BigQuery table using a staging table and SQL MERGE to prevent duplicates."""
    import pandas as pd
    # pyrefly: ignore [missing-import]
    from google.cloud import bigquery
    
    staging_table_id = f"{table_id}_staging"
    
    # Read data into Pandas DataFrame
    df = pd.read_csv(local_csv_path)
    
    # 1. Load DataFrame to Staging Table (Overwrite)
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )
    
    print(f" -> Loading data into staging table {dataset_id}.{staging_table_id}...")
    staging_ref = client.dataset(dataset_id).table(staging_table_id)
    load_job = client.load_table_from_dataframe(df, staging_ref, job_config=job_config)
    load_job.result()  # Wait for upload to complete
    
    # 2. Create Target Table if it does not exist
    target_ref = client.dataset(dataset_id).table(table_id)
    try:
        client.get_table(target_ref)
    except Exception:
        print(f" -> Target table {table_id} does not exist. Creating it with staging schema...")
        staging_table = client.get_table(staging_ref)
        target_table = bigquery.Table(target_ref, schema=staging_table.schema)
        client.create_table(target_table)
        
    # 3. Perform MERGE Statement to Upsert data (Prevent duplicates)
    schema = client.get_table(staging_ref).schema
    columns = [field.name for field in schema]
    
    join_condition = " AND ".join([f"T.{key} = S.{key}" for key in primary_keys])
    insert_cols = ", ".join(columns)
    insert_vals = ", ".join([f"S.{col}" for col in columns])
    
    # If there are columns that are not primary keys, update them
    non_keys = [col for col in columns if col not in primary_keys]
    update_clause = ""
    if non_keys:
        update_clause = "WHEN MATCHED THEN UPDATE SET " + ", ".join([f"T.{col} = S.{col}" for col in non_keys])
        
    merge_query = f"""
    MERGE `{client.project}.{dataset_id}.{table_id}` T
    USING `{client.project}.{dataset_id}.{staging_table_id}` S
    ON {join_condition}
    {update_clause}
    WHEN NOT MATCHED THEN
      INSERT ({insert_cols})
      VALUES ({insert_vals})
    """
    
    print(f" -> Merging staging into target table {dataset_id}.{table_id}...")
    query_job = client.query(merge_query)
    query_job.result()  # Wait for query to complete
    
    # 4. Clean up staging table
    client.delete_table(staging_ref)
    print(f" -> Load complete for {table_id}!")


# -------------------------------------------------------------
# AWS REDSHIFT LOADING IMPLEMENTATION
# -------------------------------------------------------------
def load_to_redshift(s3_client, redshift_data_client, config, table_name, local_csv_path, primary_keys, ddl):
    """Loads CSV to Amazon Redshift via S3 upload & temp staging table COPY to avoid duplicates."""
    import time
    
    bucket = config['s3_bucket']
    s3_key = f"staging/{table_name}.csv"
    s3_uri = f"s3://{bucket}/{s3_key}"
    
    # 1. Upload CSV to S3
    print(f" -> Uploading {local_csv_path} to s3://{bucket}/{s3_key}...")
    s3_client.upload_file(local_csv_path, bucket, s3_key)
    
    staging_table = f"{table_name}_staging"
    join_condition = " AND ".join([f"T.{key} = S.{key}" for key in primary_keys])
    
    # SQL script to build table, copy to staging, delete target duplicates, insert staging
    sql_script = f"""
    -- Create Target Table if it does not exist
    {ddl}

    -- Create Temp Table for staging
    CREATE TEMP TABLE {staging_table} (LIKE {table_name});

    -- COPY from S3 to Staging
    COPY {staging_table}
    FROM '{s3_uri}'
    IAM_ROLE '{config['iam_role']}'
    FORMAT AS CSV
    IGNOREHEADER 1
    DATEFORMAT 'auto'
    TIMEFORMAT 'auto';

    -- Deduplicate: Delete existing records in target matching staging keys
    DELETE FROM {table_name}
    USING {staging_table} S
    WHERE {join_condition.replace('T.', f'{table_name}.')};

    -- Insert all rows from staging to target
    INSERT INTO {table_name}
    SELECT * FROM {staging_table};

    -- Drop staging table
    DROP TABLE {staging_table};
    """
    
    print(f" -> Triggering Redshift query execution for {table_name}...")
    response = redshift_data_client.execute_statement(
        ClusterIdentifier=config['cluster_id'],
        Database=config['database'],
        DbUser=config['db_user'],
        Sql=sql_script
    )
    statement_id = response['Id']
    
    # Poll for completion
    while True:
        status_res = redshift_data_client.describe_statement(Id=statement_id)
        status = status_res['Status']
        if status == 'FINISHED':
            print(f" -> Redshift execution finished successfully for {table_name}!")
            break
        elif status in ('FAILED', 'ABORTED'):
            raise Exception(f"Redshift statement failed with status '{status}': {status_res.get('Error')}")
        time.sleep(2)


# -------------------------------------------------------------
# MAIN WAREHOUSE LOADING ORCHESTRATOR
# -------------------------------------------------------------
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Table definitions
    tables = {
        'dim_customers': {
            'csv': os.path.join(base_dir, 'dim_customers.csv'),
            'keys': ['customer_id'],
            'redshift_ddl': """
                CREATE TABLE IF NOT EXISTS dim_customers (
                    customer_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(150),
                    email VARCHAR(150),
                    signup_date DATE,
                    city VARCHAR(100),
                    state VARCHAR(100),
                    country VARCHAR(50)
                );
            """
        },
        'dim_products': {
            'csv': os.path.join(base_dir, 'dim_products.csv'),
            'keys': ['product_id'],
            'redshift_ddl': """
                CREATE TABLE IF NOT EXISTS dim_products (
                    product_id VARCHAR(50) PRIMARY KEY,
                    product_name VARCHAR(150),
                    category VARCHAR(100),
                    price DECIMAL(10, 2)
                );
            """
        },
        'fact_sales': {
            'csv': os.path.join(base_dir, 'fact_sales.csv'),
            'keys': ['order_id', 'product_id'],
            'redshift_ddl': """
                CREATE TABLE IF NOT EXISTS fact_sales (
                    order_id VARCHAR(50),
                    customer_id VARCHAR(50) REFERENCES dim_customers(customer_id),
                    product_id VARCHAR(50) REFERENCES dim_products(product_id),
                    quantity INTEGER,
                    unit_price DECIMAL(10, 2),
                    item_total DECIMAL(10, 2),
                    order_total DECIMAL(10, 2),
                    order_date TIMESTAMP,
                    PRIMARY KEY (order_id, product_id)
                );
            """
        }
    }

    # Verify files exist
    for t_name, t_info in tables.items():
        if not os.path.exists(t_info['csv']):
            print(f"Error: Cleaned data file not found: {t_info['csv']}")
            print("Please run 'python etl_process.py' first.")
            sys.exit(1)

    print("=" * 60)
    print(f"LOADING DATA INTO CLOUD DATA WAREHOUSE: {DW_TYPE.upper()}")
    print("=" * 60)

    try:
        if DW_TYPE == 'bigquery':
            # pyrefly: ignore [missing-import]
            from google.cloud import bigquery
            
            print(f"Initializing BigQuery Client (Project: {BQ_PROJECT_ID})...")
            client = bigquery.Client(project=BQ_PROJECT_ID)
            
            # Ensure dataset exists
            dataset_ref = client.dataset(BQ_DATASET_ID)
            try:
                client.get_dataset(dataset_ref)
                print(f"Dataset '{BQ_DATASET_ID}' verified.")
            except Exception:
                print(f"Dataset '{BQ_DATASET_ID}' not found. Creating it...")
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                client.create_dataset(dataset)
                
            for table_name, info in tables.items():
                print(f"\nLoading {table_name}...")
                load_to_bigquery(client, BQ_DATASET_ID, table_name, info['csv'], info['keys'])

        elif DW_TYPE == 'redshift':
            import boto3
            
            print("Initializing AWS clients (S3 & Redshift Data)...")
            s3_client = boto3.client('s3', region_name=AWS_REGION)
            redshift_data_client = boto3.client('redshift-data', region_name=AWS_REGION)
            
            rs_config = {
                's3_bucket': S3_BUCKET_NAME,
                'cluster_id': REDSHIFT_CLUSTER_ID,
                'database': REDSHIFT_DATABASE,
                'db_user': REDSHIFT_DB_USER,
                'iam_role': REDSHIFT_IAM_ROLE_ARN
            }
            
            for table_name, info in tables.items():
                print(f"\nLoading {table_name}...")
                load_to_redshift(
                    s3_client=s3_client,
                    redshift_data_client=redshift_data_client,
                    config=rs_config,
                    table_name=table_name,
                    local_csv_path=info['csv'],
                    primary_keys=info['keys'],
                    ddl=info['redshift_ddl']
                )
        else:
            print(f"Error: Unknown DW_TYPE '{DW_TYPE}'. Set it to 'bigquery' or 'redshift'.")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("CLOUD DATA WAREHOUSE LOAD FINISHED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "!" * 60)
        print(f"FATAL ERROR DURING ETL WAREHOUSE LOADING:")
        print(str(e))
        print("!" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()
