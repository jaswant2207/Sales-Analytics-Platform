# Power BI & Tableau Connection Guide to BigQuery / Redshift

This guide outlines step-by-step connection workflows and authentication setups to connect Power BI Desktop and Tableau to Google BigQuery or Amazon Redshift.

---

## SECTION 1: GOOGLE BIGQUERY CONNECTIONS

### 1. Prerequisites & Authentication Setup (BigQuery)

Before connecting Power BI or Tableau, choose your Authentication Method:

#### Option A: OAuth 2.0 (Organizational Account - Recommended for Power BI/Tableau Desktop)
- Sign in directly with your Google Workspace / GCP email account during connection.

#### Option B: Service Account JSON Key (Recommended for Automated Refresh & Production Servers)
1. Go to **GCP Console** -> **IAM & Admin** -> **Service Accounts**.
2. Click **Create Service Account** (e.g., `powerbi-bq-reader@your-project.iam.gserviceaccount.com`).
3. Grant the required IAM Roles:
   - **BigQuery Data Viewer** (`roles/bigquery.dataViewer`): To read tables & views.
   - **BigQuery Job User** (`roles/bigquery.jobUser`): To run queries and jobs.
4. Under **Keys**, click **Add Key** -> **Create new key** -> Select **JSON**. Download the `.json` file.

---

### 2. Connecting Power BI Desktop to BigQuery

1. Open **Power BI Desktop**.
2. On the **Home** tab, click **Get Data** -> Select **Google BigQuery** -> Click **Connect**.
3. **Sign In**: Select **Organizational Account** -> Click **Sign in** -> Log in via browser window with your GCP account.
4. Choose **Data Connectivity Mode**:
   - **DirectQuery** *(Recommended)*: Queries run live in BigQuery. No data size limits.
   - **Import**: Downloads snapshot into Power BI memory. Faster visuals, but capped at 1GB/model unless Premium.
5. In the **Navigator** pane, expand your GCP Project ID -> Select your dataset (`ecommerce_dw`) -> Select tables (`dim_customers`, `dim_products`, `fact_sales`).
6. Click **Load** or **Transform Data**.

---

### 3. Connecting Tableau Desktop to BigQuery

1. Open **Tableau Desktop**.
2. Under **To a Server**, click **Google BigQuery**.
3. A browser window opens: Select your Google account and grant Tableau permission.
4. In Tableau Data Source tab:
   - Select **Billing Project** (your GCP project).
   - Select **Project** and **Dataset** (`ecommerce_dw`).
5. Drag tables (`fact_sales`, `dim_customers`, `dim_products`) onto the canvas.
6. Choose Connection Type:
   - **Live**: Executes SQL queries directly on BigQuery.
   - **Extract**: Creates a `.hyper` snapshot file locally.

---

## SECTION 2: AMAZON REDSHIFT CONNECTIONS

### 1. Prerequisites & Authentication Setup (Redshift)

#### Required Parameters:
- **Server / Host**: e.g., `your-cluster.xyz.us-east-1.redshift.amazonaws.com`
- **Port**: `5439` (default Redshift port)
- **Database**: `dev` or your database name
- **Username & Password**: Database user credentials or IAM credentials.

#### Network & Driver Requirements:
1. **Public Accessibility / VPC**: Ensure your Redshift cluster Security Group allows inbound TCP traffic on port `5439` from your IP / Power BI gateway / Tableau Server IP.
2. **Amazon Redshift ODBC Driver**: Download and install official Redshift ODBC drivers on your Windows machine if prompted.

---

### 2. Connecting Power BI Desktop to Redshift

1. Open **Power BI Desktop**.
2. Click **Get Data** -> Search for **Amazon Redshift** -> Click **Connect**.
3. Enter Connection Info:
   - **Server**: `your-cluster-name.xxxxxx.us-east-1.redshift.amazonaws.com:5439`
   - **Database**: `dev`
4. Select Data Connectivity Mode: **DirectQuery** or **Import**.
5. Enter **Credentials**: Select **Database** tab -> Enter your `Username` and `Password`.
6. Click **Connect** -> Select tables in **Navigator** -> Click **Load**.

---

### 3. Connecting Tableau Desktop to Redshift

1. Open **Tableau Desktop**.
2. Under **To a Server**, click **Amazon Redshift**.
3. In the connection dialog:
   - **Server**: `your-cluster-name.xxxxxx.us-east-1.redshift.amazonaws.com`
   - **Port**: `5439`
   - **Database**: `dev`
   - **Authentication**: Select `Username and Password` or `IAM`.
   - **Username / Password**: Enter Redshift DB credentials.
4. Click **Sign In**.
5. Select Schema (e.g., `public`) -> Drag `fact_sales`, `dim_customers`, `dim_products` into the canvas -> Select **Live** or **Extract**.

---

## SUMMARY COMPARISON: IMPORT VS. DIRECTQUERY / LIVE

| Metric | DirectQuery / Live Connection | Import / Extract Connection |
| :--- | :--- | :--- |
| **Data Recency** | Real-time (queries warehouse directly on visual interaction) | Scheduled Refresh (e.g. 8x/day) |
| **Warehouse Costs** | Higher (every visual interaction runs BigQuery/Redshift SQL) | Lower (only queries warehouse during scheduled refreshes) |
| **Data Size Limit** | Virtually Unlimited | Limited by BI Desktop / Server Memory |
| **Performance** | Dependent on Warehouse Tuning (Partitioning/DistKeys) | Fast in-memory engine (Power BI VertiPaq / Tableau Hyper) |
