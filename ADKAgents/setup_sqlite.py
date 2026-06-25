"""Create a local bank_data.db SQLite database from the JSON seed files."""
import json
import sqlite3

conn = sqlite3.connect("bank_data.db")
c = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY, name TEXT, dob TEXT, postcode TEXT,
    address TEXT, age INTEGER, gender TEXT, phone TEXT, email TEXT,
    occupation TEXT, annual_income_band TEXT, life_stage TEXT
);
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY, customer_id TEXT, product_type TEXT,
    account_type TEXT, opened_date TEXT, balance REAL, interest_rate REAL
);
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY, account_id TEXT, description TEXT,
    amount REAL, type TEXT, category TEXT, date TEXT
);
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY, product_name TEXT, product_type TEXT,
    interest_rate_pa REAL, monthly_fee REAL, min_deposit REAL,
    max_balance REAL, access_type TEXT, notice_period_days INTEGER,
    term_months INTEGER, features TEXT, target_segment TEXT,
    min_age INTEGER, is_active INTEGER
);
""")

for table, filepath in [
    ("customers",    "bq_seed/customers.json"),
    ("accounts",     "bq_seed/accounts.json"),
    ("transactions", "bq_seed/transactions.json"),
    ("products",     "bq_seed/products.json"),
]:
    with open(filepath) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if not rows:
        continue
    cols = list(rows[0].keys())
    placeholders = ",".join(["?" for _ in cols])
    col_names = ",".join(cols)
    c.executemany(
        f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
        [[r.get(col) for col in cols] for r in rows],
    )
    print(f"  {table}: {len(rows)} rows loaded")

conn.commit()
conn.close()
print("bank_data.db ready.")
