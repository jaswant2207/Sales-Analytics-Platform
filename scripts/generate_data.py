import csv
import datetime
import os
import random
import sys

# Attempt to import Faker, install if missing (optional but helpful)
try:
    # pyrefly: ignore [missing-import]
    from faker import Faker
except ImportError:
    print("The 'Faker' library is not installed.")
    print("Attempting to install 'Faker' using pip...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Faker"])
        # pyrefly: ignore [missing-import]
        from faker import Faker
        print("'Faker' successfully installed!")
    except Exception as e:
        print(f"Failed to install 'Faker' automatically: {e}")
        print("Please run 'pip install Faker' manually and run this script again.")
        sys.exit(1)

def corrupt_date_format(dt, is_datetime=False):
    """Corrupts date formatting to simulate real-world data entry inconsistencies."""
    formats = [
        '%m/%d/%Y',        # MM/DD/YYYY
        '%d-%m-%Y',        # DD-MM-YYYY
        '%Y/%m/%d',        # YYYY/MM/DD
        '%B %d, %Y',       # Month Day, Year
    ]
    if is_datetime:
        # Time-based formats
        time_formats = [
            '%m/%d/%Y %H:%M',
            '%d-%m-%Y %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            'timestamp'  # Unix timestamp
        ]
        fmt = random.choice(time_formats)
        if fmt == 'timestamp':
            return str(int(dt.timestamp()))
        return dt.strftime(fmt)
    else:
        fmt = random.choice(formats)
        return dt.strftime(fmt)

def main():
    # Set seeds for reproducibility
    random.seed(42)
    fake = Faker()
    fake.seed_instance(42)

    print("Generating messy e-commerce sales data...")

    # Define paths (support running from root or scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = project_root if os.path.exists(os.path.join(project_root, 'index.html')) else script_dir

    customers_file = os.path.join(output_dir, 'customers.csv')
    products_file = os.path.join(output_dir, 'products.csv')
    orders_file = os.path.join(output_dir, 'orders.csv')

    # 1. Generate Customers
    # 500 customers with names, emails, signup dates, and locations
    print("Generating 500 customers (plus duplicates and anomalies)...")
    customers = []
    
    # We want customer signup dates to range from before and during the order period.
    # Order period is last 2 years: 2024-07-05 to 2026-07-05.
    # Signups start from 2023-01-01 to 2026-04-01.
    pre_start = datetime.date(2023, 1, 1)
    pre_end = datetime.date(2024, 7, 4)
    pre_delta = pre_end - pre_start

    mid_start = datetime.date(2024, 7, 5)
    mid_end = datetime.date(2026, 4, 1)
    mid_delta = mid_end - mid_start

    for i in range(1, 501):
        customer_id = f"C{i:03d}"
        
        # Name
        first_name = fake.first_name()
        last_name = fake.last_name()
        name = f"{first_name} {last_name}"
        
        # Email (guaranteed unique and realistic)
        email_domain = fake.free_email_domain()
        email = f"{first_name.lower()}.{last_name.lower()}.{i}@{email_domain}"
        
        # Signup Date (60% before order period, 40% during order period)
        if i <= 300:
            random_days = random.randint(0, pre_delta.days)
            signup_date = pre_start + datetime.timedelta(days=random_days)
        else:
            random_days = random.randint(0, mid_delta.days)
            signup_date = mid_start + datetime.timedelta(days=random_days)
            
        # Location
        city = fake.city()
        state = fake.state()
        country = "United States"
        
        customers.append({
            'customer_id': customer_id,
            'name': name,
            'email': email,
            'signup_date': signup_date,  # Keep as datetime.date for order generation logic
            'city': city,
            'state': state,
            'country': country
        })

    # Apply corruption to customer data before writing to CSV
    messy_customers = []
    missing_email_count = 0
    inconsistent_cust_date_count = 0

    for c in customers:
        c_copy = c.copy()
        
        # Inconsistent Date Format (5% chance)
        if random.random() < 0.05:
            c_copy['signup_date'] = corrupt_date_format(c['signup_date'], is_datetime=False)
            inconsistent_cust_date_count += 1
        else:
            c_copy['signup_date'] = c['signup_date'].strftime('%Y-%m-%d')
            
        # Missing Email (2% chance)
        if random.random() < 0.02:
            c_copy['email'] = random.choice([None, "", "NaN"])
            missing_email_count += 1
            
        messy_customers.append(c_copy)

    # Add duplicate customer entries (data cleaning practice)
    # A. Exact row duplicates (5 entries)
    exact_dupes = random.sample(messy_customers, k=5)
    for dupe in exact_dupes:
        messy_customers.append(dupe.copy())
        
    # B. CRM duplicate entries (5 entries - same person, different ID and signup date)
    crm_dupes = random.sample(customers, k=5)
    for idx, dupe in enumerate(crm_dupes):
        new_id = f"C{501 + idx:03d}"
        new_signup = dupe['signup_date'] + datetime.timedelta(days=random.randint(10, 100))
        
        # Decide date formatting for the duplicate entry
        if random.random() < 0.05:
            signup_str = corrupt_date_format(new_signup, is_datetime=False)
            inconsistent_cust_date_count += 1
        else:
            signup_str = new_signup.strftime('%Y-%m-%d')
            
        messy_customers.append({
            'customer_id': new_id,
            'name': dupe['name'],
            'email': dupe['email'],
            'signup_date': signup_str,
            'city': dupe['city'],
            'state': dupe['state'],
            'country': dupe['country']
        })

    # Write customers to CSV
    with open(customers_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['customer_id', 'name', 'email', 'signup_date', 'city', 'state', 'country'])
        writer.writeheader()
        writer.writerows(messy_customers)
    print(f"Successfully saved {len(messy_customers)} customer rows to {customers_file}")

    # 2. Generate Products
    # 50 products across 5 categories with prices
    print("Generating 50 products...")
    
    product_templates = {
        'Electronics': [
            "QuantumSound Wireless Headphones", "AeroCharge Power Bank", "VisionPro 4K Monitor", 
            "Titanium-X Smart Watch", "LunaBeam Portable Projector", "Apex Router Wi-Fi 6",
            "SoundWave Bluetooth Speaker", "VoltDock Charging Station", "ClearVoice USB Microphone",
            "NovaFit Fitness Tracker"
        ],
        'Clothing': [
            "EcoSoft Organic Cotton T-Shirt", "UrbanStretch Denim Jeans", "WindShield Active Windbreaker",
            "ThermaLoft Puffer Jacket", "BreezeWalk Running Socks", "SummitFit Athletic Hoodie",
            "ClassicFit Chino Pants", "MerinoComfort Wool Sweater", "DryLite Training Shorts",
            "AllWeather Waterproof Gloves"
        ],
        'Home & Kitchen': [
            "ChefPrecision Knife Set", "BaristaBlend Espresso Machine", "PureAir HEPA Purifier",
            "FlexSpatula Silicone Set", "EmberGlow Scented Candle", "HydroFlow Water Filter",
            "SmartCook Air Fryer", "BambooSleep Bed Pillows", "ThermalShield Travel Mug",
            "EcoClean Robot Vacuum"
        ],
        'Beauty': [
            "HydroGlow Hyaluronic Serum", "VelvetMatte Liquid Lipstick", "ClayPure Detoxifying Mask",
            "SilkRadiance Face Oil", "SatinFinish Setting Powder", "CocoaButter Hand Cream",
            "HerbalShine Volumizing Shampoo", "RoseDew Facial Toner", "SunShield SPF 50 Sunscreen",
            "CharcoalGlow Whitening Toothpaste"
        ],
        'Sports & Outdoors': [
            "TrailBlazer Hiking Backpack", "HydroSip Insulated Flask", "FlexFoam Yoga Mat",
            "CampComfort Sleeping Bag", "AeroSpoke Bicycle Pump", "PeakGrab Climbing Chalk Bag",
            "TrekPole Carbon Trekking Poles", "AquaGlide Swim Goggles", "SunBlocker Beach Tent",
            "SpeedStride Resistance Bands"
        ]
    }

    price_ranges = {
        'Electronics': (20, 500),
        'Clothing': (15, 120),
        'Home & Kitchen': (10, 300),
        'Beauty': (8, 80),
        'Sports & Outdoors': (12, 200)
    }

    products = []
    product_idx = 1
    for category, names in product_templates.items():
        min_p, max_p = price_ranges[category]
        for name in names:
            product_id = f"P{product_idx:02d}"
            # Generate realistic price ending in .99
            price = float(random.randint(min_p, max_p)) - 0.01
            
            products.append({
                'product_id': product_id,
                'product_name': name,
                'category': category,
                'price': f"{price:.2f}"
            })
            product_idx += 1

    # Write products to CSV
    with open(products_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['product_id', 'product_name', 'category', 'price'])
        writer.writeheader()
        writer.writerows(products)
    print(f"Successfully saved {len(products)} products to {products_file}")

    # 3. Generate Orders
    # 8,000 orders over the last 2 years, linking a customer to 1-4 products,
    # with realistic order dates (more on weekends and Nov-Dec).
    print("Generating 8,000 orders...")
    
    # Define date range: 2024-07-05 to 2026-07-05
    start_date = datetime.date(2024, 7, 5)
    end_date = datetime.date(2026, 7, 5)
    delta = end_date - start_date
    days = [start_date + datetime.timedelta(days=i) for i in range(delta.days + 1)]

    # Compute weights for all days
    day_weights = []
    for day in days:
        weight = 1.0
        # Weekend (Saturday=5, Sunday=6)
        if day.weekday() in (5, 6):
            weight *= 1.8
        # Holiday season (November=11, December=12)
        if day.month in (11, 12):
            weight *= 2.5
        day_weights.append(weight)

    clean_order_items = []
    weekend_count = 0
    holiday_count = 0
    total_items = 0

    for i in range(1, 8001):
        order_id = f"O{i:05d}"
        
        # Pick a random customer
        customer = random.choice(customers)
        cust_signup = customer['signup_date'] # Already datetime.date object
        
        # Valid order date range: from max(signup, start_date) to end_date
        order_start = max(cust_signup, start_date)
        
        # Filter valid days and their weights
        valid_indices = [idx for idx, d in enumerate(days) if d >= order_start]
        if not valid_indices:
            # Fallback if signup date is somehow after end_date (should not happen based on constraints)
            valid_indices = [len(days) - 1]
            
        valid_days = [days[idx] for idx in valid_indices]
        valid_weights = [day_weights[idx] for idx in valid_indices]
        
        # Sample order date
        sampled_day = random.choices(valid_days, weights=valid_weights, k=1)[0]
        
        # Track statistics
        if sampled_day.weekday() in (5, 6):
            weekend_count += 1
        if sampled_day.month in (11, 12):
            holiday_count += 1
            
        # Add random time of day
        random_hour = random.randint(0, 23)
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)
        order_datetime = datetime.datetime.combine(
            sampled_day, 
            datetime.time(random_hour, random_minute, random_second)
        )
        
        # Determine number of products (1 to 4)
        num_products = random.choices([1, 2, 3, 4], weights=[0.50, 0.30, 0.15, 0.05])[0]
        
        # Select products
        sampled_products = random.sample(products, k=num_products)
        
        for prod in sampled_products:
            # Generate quantity (1 to 3)
            quantity = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03])[0]
            
            clean_order_items.append({
                'order_id': order_id,
                'customer_id': customer['customer_id'],
                'product_id': prod['product_id'],
                'quantity': quantity,
                'unit_price': float(prod['price']),
                'order_date': order_datetime
            })

    # Apply corruption to order items
    messy_order_items = []
    inconsistent_order_date_count = 0
    messy_qty_count = 0
    messy_price_count = 0

    for item in clean_order_items:
        item_copy = item.copy()
        
        # 1. Inconsistent date formats (5% chance)
        if random.random() < 0.05:
            item_copy['order_date'] = corrupt_date_format(item['order_date'], is_datetime=True)
            inconsistent_order_date_count += 1
        else:
            item_copy['order_date'] = item['order_date'].strftime('%Y-%m-%d %H:%M:%S')
            
        # 2. Negative or zero order quantity (0.3% chance of error)
        if random.random() < 0.003:
            item_copy['quantity'] = random.choice([0, -1, -2])
            messy_qty_count += 1
            
        # 3. Negative or zero unit price (0.3% chance of error)
        if random.random() < 0.003:
            item_copy['unit_price'] = f"{random.choice([0.00, -10.00, -49.99]):.2f}"
            messy_price_count += 1
        else:
            item_copy['unit_price'] = f"{item['unit_price']:.2f}"
            
        messy_order_items.append(item_copy)

    # Write orders to CSV
    with open(orders_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['order_id', 'customer_id', 'product_id', 'quantity', 'unit_price', 'order_date'])
        writer.writeheader()
        writer.writerows(messy_order_items)
    print(f"Successfully saved {len(messy_order_items)} order items (from 8,000 unique orders) to {orders_file}")

    # Print validation statistics
    print("\n--- Generation Summary & Validation ---")
    print(f"Customers generated : {len(customers)}")
    print(f"Total customer rows : {len(messy_customers)} (inc. duplicates)")
    print(f"Products generated  : {len(products)}")
    print(f"Orders generated    : 8000")
    print(f"Total order rows    : {len(messy_order_items)}")
    print(f"Average items/order : {len(messy_order_items) / 8000:.2f}")
    
    # Validate weekend distribution
    pct_weekend = (weekend_count / 8000) * 100
    print(f"Weekend orders      : {weekend_count} ({pct_weekend:.2f}% of total, expected ~42% vs baseline 28.6%)")
    
    # Validate holiday season distribution
    pct_holiday = (holiday_count / 8000) * 100
    print(f"Nov-Dec orders      : {holiday_count} ({pct_holiday:.2f}% of total, expected ~33% vs baseline 16.7%)")
    
    print("\n--- Messiness & Anomalies Summary (for cleaning practice) ---")
    print(f"Duplicate customer rows  : {len(messy_customers) - len(customers)} (5 exact, 5 CRM ID dupes)")
    print(f"Missing customer emails  : {missing_email_count}")
    print(f"Messy customer signups   : {inconsistent_cust_date_count} rows")
    print(f"Messy order dates        : {inconsistent_order_date_count} rows")
    print(f"Negative/zero quantities : {messy_qty_count} rows")
    print(f"Negative/zero unit prices: {messy_price_count} rows")
    print("-------------------------------------------------------------")

if __name__ == '__main__':
    main()
