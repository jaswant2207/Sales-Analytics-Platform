-- =============================================================================
-- E-COMMERCE STAR SCHEMA DDL FOR GOOGLE BIGQUERY & AMAZON REDSHIFT
-- =============================================================================

-- =============================================================================
-- 1. GOOGLE BIGQUERY DDL
-- =============================================================================

-- Dimension: Customers
CREATE OR REPLACE TABLE `your_project_id.ecommerce_dw.dim_customers`
(
    customer_id STRING NOT NULL OPTIONS(description="Unique Customer Identifier (Primary Key)"),
    name STRING OPTIONS(description="Full Name"),
    email STRING OPTIONS(description="Unique Email Address"),
    signup_date DATE OPTIONS(description="Customer Signup Date"),
    city STRING OPTIONS(description="Customer City"),
    state STRING OPTIONS(description="Customer State"),
    country STRING OPTIONS(description="Customer Country"),
    PRIMARY KEY (customer_id) NOT ENFORCED
);

-- Dimension: Products
CREATE OR REPLACE TABLE `your_project_id.ecommerce_dw.dim_products`
(
    product_id STRING NOT NULL OPTIONS(description="Unique Product Identifier (Primary Key)"),
    product_name STRING OPTIONS(description="Product Name"),
    category STRING OPTIONS(description="Product Category"),
    price NUMERIC OPTIONS(description="Product Unit Price"),
    PRIMARY KEY (product_id) NOT ENFORCED
);

-- Fact Table: Sales (Optimized with Daily Partitioning and Clustering)
CREATE OR REPLACE TABLE `your_project_id.ecommerce_dw.fact_sales`
(
    order_id STRING NOT NULL OPTIONS(description="Order ID"),
    customer_id STRING NOT NULL OPTIONS(description="Foreign Key to dim_customers"),
    product_id STRING NOT NULL OPTIONS(description="Foreign Key to dim_products"),
    quantity INT64 OPTIONS(description="Quantity purchased"),
    unit_price NUMERIC OPTIONS(description="Unit price at purchase time"),
    item_total NUMERIC OPTIONS(description="Line item total (quantity * unit_price)"),
    order_total NUMERIC OPTIONS(description="Total amount for the entire order"),
    order_date TIMESTAMP OPTIONS(description="Timestamp when order was placed"),
    PRIMARY KEY (order_id, product_id) NOT ENFORCED,
    FOREIGN KEY (customer_id) REFERENCES `your_project_id.ecommerce_dw.dim_customers`(customer_id) NOT ENFORCED,
    FOREIGN KEY (product_id) REFERENCES `your_project_id.ecommerce_dw.dim_products`(product_id) NOT ENFORCED
)
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, product_id
OPTIONS(
    description="Fact table storing sales line items, partitioned by order date and clustered by customer and product IDs."
);


-- =============================================================================
-- 2. AMAZON REDSHIFT DDL
-- =============================================================================

-- Dimension: Customers (All Distribution for fast small dimension joins)
CREATE TABLE IF NOT EXISTS dim_customers
(
    customer_id VARCHAR(50) NOT NULL,
    name VARCHAR(150),
    email VARCHAR(150),
    signup_date DATE,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(50),
    PRIMARY KEY (customer_id)
)
DISTSTYLE ALL
SORTKEY (customer_id);

-- Dimension: Products (All Distribution)
CREATE TABLE IF NOT EXISTS dim_products
(
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(150),
    category VARCHAR(100),
    price DECIMAL(10, 2),
    PRIMARY KEY (product_id)
)
DISTSTYLE ALL
SORTKEY (category, product_id);

-- Fact Table: Sales (Key Distribution on customer_id + Compound Sortkey on order_date, customer_id)
CREATE TABLE IF NOT EXISTS fact_sales
(
    order_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES dim_customers(customer_id),
    product_id VARCHAR(50) NOT NULL REFERENCES dim_products(product_id),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    item_total DECIMAL(10, 2),
    order_total DECIMAL(10, 2),
    order_date TIMESTAMP NOT NULL,
    PRIMARY KEY (order_id, product_id)
)
DISTSTYLE KEY
DISTKEY (customer_id)
COMPOUND SORTKEY (order_date, customer_id, product_id);
