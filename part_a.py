import os, sqlite3
import numpy as np
import pandas as pd

os.makedirs("data/clean", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("sql", exist_ok=True)

# Audit
customers_raw = pd.read_csv("data/raw/customers.csv")
products_raw = pd.read_csv("data/raw/products.csv")
orders_raw = pd.read_csv("data/raw/orders.csv")
tickets_raw = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)

# Clean Customers
customers = customers_raw.copy()
customers['city'] = customers['city'].astype(str).str.strip().str.title()
def clean_g(g):
    s = str(g).strip().lower()
    if s in ['male', 'm']: return 'male'
    if s in ['female', 'f']: return 'female'
    return 'unknown'
customers['gender'] = customers['gender'].apply(clean_g)
customers['age'] = pd.to_numeric(customers['age'], errors='coerce')
customers.loc[(customers['age'] < 10) | (customers['age'] > 100), 'age'] = np.nan
customers['age'] = customers['age'].fillna(customers.groupby('city')['age'].transform('median'))
customers['signup_date'] = pd.to_datetime(customers['signup_date'])
customers.to_csv("data/clean/customers.csv", index=False)

# Clean Orders
orders = orders_raw.copy()
orders['order_ts'] = pd.to_datetime(orders['order_ts'], errors='coerce')
orders = orders.drop_duplicates()
orders = orders.sort_values('order_ts', ascending=False).drop_duplicates(subset=['order_id'], keep='first')
orders['order_amount'] = pd.to_numeric(orders['order_amount'], errors='coerce')
orders = orders.merge(products_raw[['product_id', 'price_inr', 'category']], on='product_id', how='left')

missing_amt = orders['order_amount'].isna()
orders.loc[missing_amt, 'order_amount'] = np.round(orders['price_inr'] * orders['quantity'] * (1 - orders['discount_pct']/100.0), 2)[missing_amt]

orders['delivery_minutes'] = pd.to_numeric(orders['delivery_minutes'], errors='coerce')
orders.loc[orders['delivery_minutes'] < 0, 'delivery_minutes'] = np.nan

completed_mask = (orders['status'] == 'completed') & (orders['delivery_minutes'].isna())
cat_medians = orders[orders['status'] == 'completed'].groupby('category')['delivery_minutes'].transform('median')
orders.loc[completed_mask, 'delivery_minutes'] = cat_medians[completed_mask]

orders = orders.drop(columns=['price_inr', 'category'])
orders['order_ts'] = orders['order_ts'].dt.strftime('%Y-%m-%d %H:%M:%S')

orders.to_csv("data/clean/orders.csv", index=False)
products_raw.to_csv("data/clean/products.csv", index=False)

# Store SQLite
conn = sqlite3.connect("data/instamart.db")
customers.to_sql("customers", conn, if_exists="replace", index=False)
products_raw.to_sql("products", conn, if_exists="replace", index=False)
orders.to_sql("orders", conn, if_exists="replace", index=False)
conn.close()
print("Part A complete.")
