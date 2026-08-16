#!/usr/bin/env python3
"""
Production-Ready ETL Analytics Local & Cloud Dashboard Server
Serves the web UI and provides the REST API endpoints for analytics.
Supports dynamic $PORT assignment, automated data bootstrapping, and cloud deployment.
"""

import http.server
import socketserver
import json
import os
import sys
import webbrowser
import signal

# Dynamic port assignment for cloud platforms (Render, Railway, Heroku, Cloud Run)
PORT = int(os.environ.get('PORT', os.environ.get('SERVER_PORT', 8000)))
HOST = os.environ.get('HOST', '0.0.0.0')
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def ensure_warehouse_data():
    """Ensures warehouse CSV datasets are ready. If missing, auto-generates them."""
    customers_path = os.path.join(DIRECTORY, 'dim_customers.csv')
    products_path = os.path.join(DIRECTORY, 'dim_products.csv')
    sales_path = os.path.join(DIRECTORY, 'fact_sales.csv')

    if not (os.path.exists(customers_path) and os.path.exists(products_path) and os.path.exists(sales_path)):
        print("[INFO] Cleaned warehouse files missing. Auto-bootstrapping datasets...")
        try:
            # Check raw CSVs
            raw_cust = os.path.join(DIRECTORY, 'customers.csv')
            if not os.path.exists(raw_cust):
                print("[INFO] Generating synthetic raw data...")
                import generate_data
                generate_data.main()

            print("[INFO] Running ETL pipeline to generate star schema tables...")
            import etl_process
            etl_process.main()
            print("[INFO] Star schema data generated successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to auto-generate warehouse data: {e}")

class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def translate_path(self, path):
        # Override translate_path to serve dashboard.html or index.html when accessing root '/'
        clean_path = path.split('?')[0]
        if clean_path in ('/', '/index.html', '/dashboard'):
            if os.path.exists(os.path.join(DIRECTORY, 'index.html')):
                return os.path.join(DIRECTORY, 'index.html')
            return os.path.join(DIRECTORY, 'dashboard.html')
        return super().translate_path(path)

    def do_GET(self):
        clean_path = self.path.split('?')[0]
        
        # Health check endpoint for cloud load balancers and uptime monitors
        if clean_path in ('/healthz', '/health', '/api/health'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'port': PORT}).encode('utf-8'))
            return

        # Data API endpoint
        if clean_path == '/api/data':
            self.serve_api_data()
        else:
            super().do_GET()

    def serve_api_data(self):
        import pandas as pd

        customers_path = os.path.join(DIRECTORY, 'dim_customers.csv')
        products_path = os.path.join(DIRECTORY, 'dim_products.csv')
        sales_path = os.path.join(DIRECTORY, 'fact_sales.csv')

        # Check if files exist or trigger on-demand generation
        if not (os.path.exists(customers_path) and os.path.exists(products_path) and os.path.exists(sales_path)):
            ensure_warehouse_data()

        if not (os.path.exists(customers_path) and os.path.exists(products_path) and os.path.exists(sales_path)):
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_data = {'error': 'Cleaned warehouse files not found. Please run python etl_process.py.'}
            self.wfile.write(json.dumps(error_data).encode('utf-8'))
            return

        try:
            # Load CSVs
            df_cust = pd.read_csv(customers_path)
            df_prod = pd.read_csv(products_path)
            df_sales = pd.read_csv(sales_path)

            # Ensure proper types
            df_sales['item_total'] = pd.to_numeric(df_sales['item_total'], errors='coerce')
            df_sales['order_date'] = pd.to_datetime(df_sales['order_date'], errors='coerce')
            df_cust['signup_date'] = pd.to_datetime(df_cust['signup_date'], errors='coerce')

            # Calculate KPI Metrics
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

            # Recent Transactions (Last 10 items)
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

            response_data = {
                'status': 'success',
                'source': 'live_api',
                'metrics': {
                    'total_revenue': round(total_revenue, 2),
                    'total_orders': total_orders,
                    'total_customers': total_customers,
                    'avg_order_value': round(avg_order_value, 2)
                },
                'category_sales': category_sales,
                'monthly_sales': monthly_sales,
                'monthly_signups': monthly_signups,
                'recent_transactions': recent_transactions
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_data = {'error': f'Failed to process warehouse data: {str(e)}'}
            self.wfile.write(json.dumps(error_data).encode('utf-8'))

def main():
    # Attempt to pre-load pandas
    try:
        import pandas as pd
    except ImportError:
        print("[WARNING] Pandas is not installed. Installing dependencies...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "numpy", "Faker"])
        import pandas as pd

    # Change to script directory to resolve paths correctly
    os.chdir(DIRECTORY)

    # Ensure warehouse data files are prepared
    ensure_warehouse_data()

    handler = DashboardHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True

    # Cloud & container detection
    is_cloud = bool(
        os.environ.get('PORT') or 
        os.environ.get('RENDER') or 
        os.environ.get('RAILWAY_ENVIRONMENT') or 
        os.environ.get('FLY_APP_NAME') or 
        os.environ.get('DOCKER') or 
        os.environ.get('CI') or
        os.environ.get('NO_BROWSER')
    )

    with socketserver.TCPServer((HOST, PORT), handler) as httpd:
        print(f"============================================================")
        print(f"  ETL ANALYTICS PRODUCTION DASHBOARD SERVER STARTED")
        print(f"============================================================")
        print(f" -> Host:    {HOST}")
        print(f" -> Port:    {PORT}")
        print(f" -> Access:  http://localhost:{PORT}")
        print(f" -> Health:  http://localhost:{PORT}/healthz")
        print(f" -> API:     http://localhost:{PORT}/api/data")
        print(f" -> Mode:    {'Cloud / Headless' if is_cloud else 'Local Desktop'}")
        print(f" -> Press Ctrl+C to stop the server")
        print(f"============================================================")

        # Open browser in local interactive desktop environment only
        if not is_cloud:
            try:
                webbrowser.open(f"http://localhost:{PORT}")
            except Exception:
                pass

        def signal_handler(signum, frame):
            print("\n[INFO] Gracefully shutting down dashboard server...")
            httpd.server_close()
            sys.exit(0)

        # Register signals for Docker / Kubernetes graceful container stops
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except Exception:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Stopping dashboard server...")
            httpd.server_close()
            sys.exit(0)

if __name__ == '__main__':
    main()
