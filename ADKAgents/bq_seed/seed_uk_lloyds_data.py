#!/usr/bin/env python3
"""
Seed BigQuery BANK_DATA with realistic UK Lloyds Banking Group data.

Generates:
  - 200 adult customers + 30 child customers (UK names, postcodes, addresses)
  - Lloyds PCA (Classic, Club Lloyds, Silver, Gold, Platinum, Student, Graduate)
  - Lloyds Savings (Easy Saver, Cash ISA, Monthly Saver, Fixed Rate Savers)
  - Child accounts (Junior Cash ISA, Children's Saver)
  - 6 months of realistic UK transactions per account
  - Loans, credit cards, investments, fixed deposits, insurance
  - Updated merchant_categories with UK merchants

Run from ADKAgents root:
    uv run python bq_seed/seed_uk_lloyds_data.py
"""

import random
from datetime import date, timedelta

from google.cloud import bigquery

PROJECT = "ltc-ipnihack-prj-11"
DATASET = "BANK_DATA"
random.seed(42)

# ── UK Names ──────────────────────────────────────────────────────────────────
MALE_NAMES = [
    "James", "Oliver", "Harry", "Jack", "George", "Noah", "Charlie", "Jacob",
    "Alfie", "Freddie", "Thomas", "William", "Joshua", "Samuel", "Henry",
    "Edward", "Max", "Oscar", "Leo", "Arthur", "Ethan", "Dylan", "Liam",
    "Daniel", "Matthew", "Alexander", "Christopher", "Andrew", "Michael",
    "David", "Robert", "Richard", "Jonathan", "Peter", "Mark", "Paul",
    "Stephen", "Patrick", "Timothy", "Simon",
]
FEMALE_NAMES = [
    "Olivia", "Amelia", "Isla", "Ava", "Emily", "Isabella", "Mia", "Poppy",
    "Ella", "Grace", "Sophia", "Charlotte", "Chloe", "Alice", "Evie",
    "Florence", "Lucy", "Sophie", "Lily", "Freya", "Jessica", "Hannah",
    "Emma", "Sarah", "Laura", "Rachel", "Claire", "Katherine", "Victoria",
    "Elizabeth", "Margaret", "Fiona", "Helen", "Louise", "Rebecca", "Natalie",
    "Samantha", "Jennifer", "Susan", "Patricia",
]
SURNAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans",
    "Wilson", "Thomas", "Roberts", "Johnson", "Lewis", "Walker", "Robinson",
    "Wood", "Thompson", "White", "Watson", "Jackson", "Wright", "Green",
    "Harris", "Cooper", "King", "Lee", "Martin", "Clarke", "Scott", "Turner",
    "Hill", "Moore", "Baker", "Adams", "Nelson", "Carter", "Mitchell",
    "Hughes", "Edwards", "Collins", "Stewart", "Morris", "Rogers", "Cook",
    "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper", "Richardson",
]

# ── UK Locations (city, county, postcode_prefix) ─────────────────────────────
UK_LOCATIONS = [
    ("London",       "Greater London",     ["SW1A", "EC1A", "W1A",  "SE1",  "N1",   "E1",   "WC2N"]),
    ("Manchester",   "Greater Manchester", ["M1",   "M2",   "M4",   "M14",  "M21"]),
    ("Birmingham",   "West Midlands",      ["B1",   "B2",   "B15",  "B16",  "B29"]),
    ("Leeds",        "West Yorkshire",     ["LS1",  "LS2",  "LS6",  "LS8",  "LS17"]),
    ("Glasgow",      "Scotland",           ["G1",   "G2",   "G12",  "G41",  "G42"]),
    ("Bristol",      "Avon",               ["BS1",  "BS2",  "BS6",  "BS8",  "BS16"]),
    ("Edinburgh",    "Scotland",           ["EH1",  "EH2",  "EH6",  "EH9",  "EH10"]),
    ("Liverpool",    "Merseyside",         ["L1",   "L2",   "L6",   "L15",  "L18"]),
    ("Sheffield",    "South Yorkshire",    ["S1",   "S2",   "S6",   "S10",  "S11"]),
    ("Cardiff",      "Wales",              ["CF10", "CF11", "CF14", "CF24", "CF5"]),
    ("Newcastle",    "Tyne and Wear",      ["NE1",  "NE2",  "NE3",  "NE5",  "NE6"]),
    ("Nottingham",   "Nottinghamshire",    ["NG1",  "NG2",  "NG3",  "NG7",  "NG8"]),
    ("Leicester",    "Leicestershire",     ["LE1",  "LE2",  "LE3",  "LE5",  "LE7"]),
    ("Oxford",       "Oxfordshire",        ["OX1",  "OX2",  "OX3",  "OX4"]),
    ("Cambridge",    "Cambridgeshire",     ["CB1",  "CB2",  "CB3",  "CB4"]),
    ("Brighton",     "East Sussex",        ["BN1",  "BN2",  "BN3"]),
    ("Southampton",  "Hampshire",          ["SO14", "SO15", "SO16", "SO17"]),
    ("Norwich",      "Norfolk",            ["NR1",  "NR2",  "NR3",  "NR4"]),
    ("Exeter",       "Devon",              ["EX1",  "EX2",  "EX4"]),
    ("York",         "North Yorkshire",    ["YO1",  "YO10", "YO24", "YO30"]),
]

STREET_TYPES = [
    "High Street", "Church Lane", "Mill Road", "Station Road", "Victoria Road",
    "Park Avenue", "King Street", "Queen Street", "The Green", "Manor Drive",
    "Oak Close", "Rose Garden", "Elm Street", "Maple Avenue", "Cedar Road",
    "Birch Way", "Willow Lane", "Orchard Close", "School Lane", "Bridge Street",
]

OCCUPATIONS = {
    "professional": [
        ("Software Engineer", 55000, 95000),
        ("Doctor (GP)", 70000, 110000),
        ("Solicitor", 45000, 85000),
        ("Architect", 42000, 75000),
        ("Chartered Accountant", 45000, 80000),
        ("Financial Analyst", 40000, 75000),
        ("Project Manager", 42000, 72000),
        ("Data Scientist", 50000, 90000),
        ("Pharmacist", 45000, 65000),
        ("Dentist", 60000, 120000),
    ],
    "managerial": [
        ("Marketing Manager", 38000, 62000),
        ("HR Manager", 35000, 58000),
        ("Operations Manager", 38000, 65000),
        ("Sales Manager", 40000, 70000),
        ("Retail Manager", 28000, 45000),
        ("Branch Manager", 35000, 55000),
    ],
    "public_sector": [
        ("Teacher", 28000, 48000),
        ("Nurse (NHS)", 27000, 40000),
        ("Police Officer", 30000, 45000),
        ("Civil Servant", 25000, 50000),
        ("Social Worker", 26000, 40000),
        ("Firefighter", 28000, 42000),
    ],
    "trades": [
        ("Electrician", 30000, 52000),
        ("Plumber", 32000, 55000),
        ("Builder", 28000, 48000),
        ("Carpenter", 26000, 44000),
    ],
    "service": [
        ("Chef", 22000, 38000),
        ("Retail Assistant", 20000, 26000),
        ("Customer Service", 20000, 28000),
        ("Administrator", 22000, 32000),
        ("Driver", 24000, 35000),
    ],
}

EMPLOYERS = [
    "NHS", "Tesco plc", "Sainsbury's Group", "Amazon UK Services",
    "BT Group", "HSBC UK Bank", "Barclays plc", "British Airways",
    "Rolls-Royce Holdings", "GlaxoSmithKline", "Unilever UK",
    "John Lewis Partnership", "Marks & Spencer plc", "Vodafone UK",
    "BP plc", "Shell UK", "Lloyds Banking Group", "KPMG UK",
    "Deloitte UK", "PricewaterhouseCoopers UK", "Accenture UK",
    "IBM UK", "Capgemini UK", "Serco Group", "Compass Group UK",
    "Royal Mail Group", "Network Rail", "Transport for London",
    "UK Government (HMRC)", "Local Council",
]

# ── Lloyds Banking Group Products ─────────────────────────────────────────────
LLOYDS_CURRENT_ACCOUNTS = [
    # (product_name, monthly_fee, interest_rate, life_stages)
    ("Classic Current Account",     0.00, 0.00, ["young_professional","family","pre_retirement","retired"]),
    ("Club Lloyds Current Account", 3.00, 0.10, ["young_professional","family","pre_retirement"]),
    ("Silver Current Account",      9.95, 0.00, ["family","pre_retirement"]),
    ("Gold Current Account",       17.00, 0.00, ["family","pre_retirement"]),
    ("Platinum Current Account",   21.00, 0.00, ["pre_retirement","retired"]),
    ("Student Current Account",     0.00, 0.00, ["student"]),
    ("Graduate Current Account",    0.00, 0.00, ["young_professional"]),
]

LLOYDS_SAVINGS = [
    # (product_name, interest_rate, min_balance, max_balance, access_type)
    ("Easy Saver",                  1.20, 1.0,      250000.0, "instant"),
    ("Club Lloyds Monthly Saver",   6.25, 25.0,      4800.0, "notice"),
    ("Cash ISA",                    4.15, 1.0,      20000.0, "instant"),
    ("Fixed Rate Saver 1 Year",     4.50, 2000.0, 5000000.0, "fixed"),
    ("Fixed Rate Saver 2 Year",     4.25, 2000.0, 5000000.0, "fixed"),
    ("Fixed Rate Saver 3 Year",     4.10, 2000.0, 5000000.0, "fixed"),
]

CHILD_ACCOUNTS = [
    ("Junior Cash ISA",   3.75, 0.0,    9000.0),
    ("Children's Saver",  3.25, 0.0,    1200.0),
]

LLOYDS_CREDIT_CARDS = [
    ("Lloyds Bank Platinum Mastercard",      30.0, 50000.0, 3.59),
    ("Lloyds Bank Cashback Mastercard",      29.9, 40000.0, 3.59),
    ("Lloyds Bank Balance Transfer Card",    29.9, 35000.0, 3.59),
    ("Lloyds Avios Rewards Mastercard",      29.9, 45000.0, 3.59),
]

LLOYDS_LOAN_TYPES = [
    ("Personal Loan",       5.9, 12, 60),
    ("Home Improvement Loan", 7.9, 24, 84),
    ("Car Finance",         6.9, 12, 60),
]

LLOYDS_MORTGAGE_LENDERS = [
    "Lloyds Bank",
    "Halifax (Lloyds Banking Group)",
    "Bank of Scotland (Lloyds Banking Group)",
]

INVESTMENT_ASSETS = [
    ("Stocks and Shares ISA",  "isa",         "equity",  0.07, "medium"),
    ("Vanguard FTSE All-World","etf",         "equity",  0.08, "medium"),
    ("Lloyds Bank OEIC Fund",  "oeic",        "equity",  0.06, "low"),
    ("UK Gilt Fund",           "bond_fund",   "debt",    0.04, "low"),
    ("FTSE 100 Tracker",       "index_fund",  "equity",  0.07, "medium"),
    ("Global Growth Fund",     "mutual_fund", "equity",  0.09, "high"),
    ("Property Fund",          "reit",        "property",0.05, "medium"),
    ("Income Fund",            "mutual_fund", "equity",  0.05, "low"),
]

INSURANCE_PRODUCTS = [
    # (type, name, insurer, min_assured, max_assured, premium_range)
    ("life",             "Lloyds Bank Level Term Life",   "Scottish Widows",       100000, 500000, (15, 80)),
    ("critical_illness", "Critical Illness Cover",        "Scottish Widows",       50000,  300000, (20, 120)),
    ("income_protection","Income Protection",             "Scottish Widows",       10000,  60000,  (25, 100)),
    ("home_buildings",   "Lloyds Bank Home Insurance",    "Lloyds Bank Insurance", 150000, 500000, (150, 400)),
    ("home_contents",    "Lloyds Bank Contents Insurance","Lloyds Bank Insurance", 20000,  80000,  (50, 180)),
    ("car",              "Lloyds Bank Car Insurance",     "Lloyds Bank Insurance", 5000,   40000,  (400, 1200)),
    ("health",           "Lloyds Bank Health Cover",      "Bupa",                  10000,  100000, (80, 300)),
]

# ── UK Transaction Merchants ──────────────────────────────────────────────────
DEBIT_MERCHANTS = {
    "groceries": [
        ("Tesco", 25, 130), ("Sainsbury's", 22, 110), ("ASDA", 18, 95),
        ("Morrisons", 20, 85), ("Waitrose & Partners", 35, 160), ("M&S Food", 28, 90),
        ("Lidl", 15, 65), ("Aldi", 14, 60), ("Ocado", 45, 130), ("Co-op Food", 10, 55),
    ],
    "transport": [
        ("TfL Oyster", 5, 18), ("National Rail", 28, 210), ("Trainline", 25, 160),
        ("Uber", 8, 38), ("BP Petrol", 45, 95), ("Shell Petrol", 44, 92),
        ("Esso", 42, 90), ("Jet2 Flights", 50, 400),
    ],
    "shopping": [
        ("Amazon", 12, 250), ("ASOS", 22, 130), ("Next", 28, 160),
        ("John Lewis", 35, 550), ("M&S Clothing", 22, 200), ("Argos", 15, 220),
        ("Currys PC World", 30, 600), ("eBay", 10, 250), ("Primark", 10, 75),
        ("H&M", 15, 90), ("Boots", 8, 55), ("Superdrug", 6, 45),
    ],
    "dining": [
        ("Pret a Manger", 5, 14), ("Costa Coffee", 3, 9), ("Greggs", 2, 8),
        ("McDonald's", 4, 14), ("Nando's", 14, 38), ("Wagamama", 12, 32),
        ("Pizza Express", 12, 45), ("Wetherspoons", 8, 22),
    ],
    "food_delivery": [
        ("Deliveroo", 12, 48), ("Just Eat", 11, 42), ("Uber Eats", 11, 45),
    ],
    "utilities": [
        ("BT Broadband", 34, 55), ("Sky TV", 25, 75), ("Virgin Media", 30, 68),
        ("EE Mobile", 20, 52), ("O2 Mobile", 15, 48), ("Vodafone UK", 15, 48),
        ("Three Mobile", 10, 38), ("giffgaff", 8, 25),
    ],
    "energy": [
        ("British Gas", 55, 220), ("EDF Energy", 50, 190), ("Octopus Energy", 42, 170),
        ("E.ON Energy", 48, 185), ("Scottish Power", 48, 185),
    ],
    "housing": [
        ("Rent Payment", 700, 2200),
    ],
    "healthcare": [
        ("NHS Prescription", 9.90, 9.90), ("Specsavers", 30, 280),
        ("Dental Practice", 25, 180), ("Bupa Health", 60, 250),
        ("Pharmacy", 6, 40),
    ],
    "entertainment": [
        ("Netflix", 10.99, 17.99), ("Spotify", 9.99, 14.99), ("Disney+", 4.99, 11.99),
        ("Amazon Prime", 8.99, 8.99), ("Sky Sports", 22, 48),
        ("Odeon Cinema", 8, 24), ("Vue Cinema", 8, 22),
        ("PureGym", 19, 30), ("The Gym Group", 17, 25),
    ],
    "insurance": [
        ("Car Insurance", 35, 120), ("Home Insurance", 18, 55),
        ("Life Insurance", 12, 80), ("Pet Insurance", 8, 35),
    ],
    "transfers": [
        ("Transfer to Savings", 100, 800),
    ],
}

INCOME_SOURCES = [
    "Salary - {}",
    "Wages - {}",
]

LIFE_STAGE_PROFILES = {
    "student": {
        "age_range": (18, 22), "income_range": (700, 1800), "employment": "part-time",
        "savings_rate": 0.05, "has_loan_pct": 0.05, "has_cc_pct": 0.15,
    },
    "young_professional": {
        "age_range": (22, 35), "income_range": (2200, 5500), "employment": "full-time",
        "savings_rate": 0.12, "has_loan_pct": 0.2, "has_cc_pct": 0.4,
    },
    "family": {
        "age_range": (30, 55), "income_range": (2800, 7000), "employment": "full-time",
        "savings_rate": 0.10, "has_loan_pct": 0.55, "has_cc_pct": 0.5,
    },
    "pre_retirement": {
        "age_range": (50, 65), "income_range": (3500, 9000), "employment": "full-time",
        "savings_rate": 0.20, "has_loan_pct": 0.3, "has_cc_pct": 0.45,
    },
    "retired": {
        "age_range": (65, 85), "income_range": (1200, 3500), "employment": "retired",
        "savings_rate": 0.15, "has_loan_pct": 0.05, "has_cc_pct": 0.3,
    },
}


# ── Helper utilities ──────────────────────────────────────────────────────────

def rdate(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def fmt(d: date) -> str:
    return d.isoformat()

def postcode(prefix: str) -> str:
    return f"{prefix} {random.randint(1,9)}{random.choice('ABCDEFGHJKLMNPQRSTUVWXY')}{random.choice('ABCDEFGHJKLMNPQRSTUVWXY')}"

def phone() -> str:
    return f"07{random.randint(700,999)}{random.randint(100000,999999)}"

def email(name: str, idx: int) -> str:
    n = name.lower().replace(" ", ".")
    domains = ["gmail.com", "hotmail.co.uk", "outlook.com", "yahoo.co.uk", "btinternet.com", "sky.com"]
    return f"{n}{idx}@{random.choice(domains)}"

def annual_income_band(annual: float) -> str:
    if annual < 20000: return "under-20000"
    if annual < 30000: return "20000-29999"
    if annual < 40000: return "30000-39999"
    if annual < 50000: return "40000-49999"
    if annual < 60000: return "50000-59999"
    if annual < 80000: return "60000-79999"
    if annual < 100000: return "80000-99999"
    return "100000-plus"


# ── Customer generation ───────────────────────────────────────────────────────

def generate_customers(n_adults=200, n_children=30):
    customers, profiles = [], []
    today = date.today()

    life_stage_dist = ["student"] * 10 + ["young_professional"] * 50 + \
                      ["family"] * 80 + ["pre_retirement"] * 40 + ["retired"] * 20

    for i in range(1, n_adults + 1):
        life_stage = random.choice(life_stage_dist)
        profile = LIFE_STAGE_PROFILES[life_stage]
        age = random.randint(*profile["age_range"])
        dob = today - timedelta(days=age * 365 + random.randint(0, 364))
        gender = random.choice(["M", "F"])
        first_name = random.choice(MALE_NAMES if gender == "M" else FEMALE_NAMES)
        surname = random.choice(SURNAMES)
        full_name = f"{first_name} {surname}"
        city, county, prefixes = random.choice(UK_LOCATIONS)
        pc = postcode(random.choice(prefixes))
        street_no = random.randint(1, 250)
        street = random.choice(STREET_TYPES)

        monthly_income = random.randint(*[x // 12 for x in profile["income_range"]])
        annual = monthly_income * 12

        # Pick occupation by life_stage
        if life_stage == "student":
            occ_group = "service"
        elif life_stage in ("young_professional", "pre_retirement"):
            occ_group = random.choice(["professional", "managerial"])
        elif life_stage == "family":
            occ_group = random.choice(["professional", "managerial", "public_sector", "trades"])
        elif life_stage == "retired":
            occ_group = random.choice(["public_sector", "service"])
        else:
            occ_group = "service"
        occ_name, occ_min, occ_max = random.choice(OCCUPATIONS[occ_group])
        employer = random.choice(EMPLOYERS) if life_stage != "retired" else "Retired"

        emp_type = profile["employment"] if life_stage != "retired" else "retired"

        customers.append({
            "customer_id": f"C{i:03d}",
            "name": full_name,
            "dob": fmt(dob),
            "postcode": pc,
            "address": f"{street_no} {street}, {city}",
            "age": age,
            "gender": gender,
            "phone": phone(),
            "email": email(full_name, i),
            "occupation": occ_name,
            "annual_income_band": annual_income_band(annual),
            "life_stage": life_stage,
        })
        profiles.append({
            "profile_id": f"P{i:03d}",
            "customer_id": f"C{i:03d}",
            "monthly_income": float(monthly_income),
            "employment_type": emp_type,
            "occupation": occ_name,
            "employer_name": employer,
            "marital_status": random.choice(
                ["single", "married", "married", "divorced"] if age > 25 else ["single"]
            ),
            "dependents": random.choices([0, 1, 2, 3], weights=[40, 25, 25, 10])[0],
            "risk_appetite": random.choices(
                ["conservative", "moderate", "moderate", "aggressive"],
                weights=[30, 40, 20, 10]
            )[0],
            "investment_experience": random.choice(["beginner", "beginner", "intermediate", "advanced"]),
            "preferred_language": "en",
            "financial_literacy": random.choice(["basic", "intermediate", "intermediate", "advanced"]),
        })

    for i in range(1, n_children + 1):
        cid = n_adults + i
        gender = random.choice(["M", "F"])
        age = random.randint(0, 17)
        dob = today - timedelta(days=age * 365 + random.randint(0, 364))
        first_name = random.choice(MALE_NAMES[:20] if gender == "M" else FEMALE_NAMES[:20])
        surname = random.choice(SURNAMES)
        # Child shares parent's address
        parent = random.choice(customers[:n_adults])
        customers.append({
            "customer_id": f"C{cid:03d}",
            "name": f"{first_name} {surname}",
            "dob": fmt(dob),
            "postcode": parent["postcode"],
            "address": parent["address"],
            "age": age,
            "gender": gender,
            "phone": "",
            "email": "",
            "occupation": "Child",
            "annual_income_band": "under-20000",
            "life_stage": "child",
        })

    return customers, profiles


# ── Account generation ────────────────────────────────────────────────────────

def generate_accounts(customers):
    accounts = []
    aid = 1
    today = date.today()

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        age = cust["age"]

        if life_stage == "child":
            # Child accounts only
            product = random.choice(CHILD_ACCOUNTS)
            opened = rdate(date(today.year - min(age, 5), 1, 1), today)
            balance = round(random.uniform(product[2], min(product[3], 3000)), 2)
            accounts.append({
                "account_id": f"A{aid:04d}", "customer_id": cid,
                "product_type": product[0], "account_type": "savings",
                "opened_date": fmt(opened), "balance": balance,
                "interest_rate": product[1],
            })
            aid += 1
            continue

        # Adults: PCA (current account)
        eligible_pcas = [p for p in LLOYDS_CURRENT_ACCOUNTS if life_stage in p[3]]
        if not eligible_pcas:
            eligible_pcas = [LLOYDS_CURRENT_ACCOUNTS[0]]
        pca = random.choice(eligible_pcas)
        opened = rdate(date(today.year - random.randint(1, 15), 1, 1), today)
        balance = round(random.uniform(200, 6000), 2)
        accounts.append({
            "account_id": f"A{aid:04d}", "customer_id": cid,
            "product_type": pca[0], "account_type": "current",
            "opened_date": fmt(opened), "balance": balance,
            "interest_rate": pca[2],
        })
        aid += 1

        # Adults: Savings account
        savings_product = random.choice(LLOYDS_SAVINGS[:4])  # avoid long fixed terms for most
        if life_stage in ("pre_retirement", "retired"):
            savings_product = random.choice(LLOYDS_SAVINGS)
        sav_balance = round(random.uniform(savings_product[2], min(savings_product[3], 25000)), 2)
        opened2 = rdate(date(today.year - random.randint(0, 8), 1, 1), today)
        accounts.append({
            "account_id": f"A{aid:04d}", "customer_id": cid,
            "product_type": savings_product[0], "account_type": "savings",
            "opened_date": fmt(opened2), "balance": sav_balance,
            "interest_rate": savings_product[1],
        })
        aid += 1

        # Cash ISA for ~40% of adults
        if life_stage not in ("student",) and random.random() < 0.4:
            isa_balance = round(random.uniform(1000, 20000), 2)
            accounts.append({
                "account_id": f"A{aid:04d}", "customer_id": cid,
                "product_type": "Cash ISA", "account_type": "isa",
                "opened_date": fmt(rdate(date(today.year - random.randint(1, 5), 4, 6), today)),
                "balance": isa_balance, "interest_rate": 4.15,
            })
            aid += 1

    return accounts


# ── Transaction generation ────────────────────────────────────────────────────

def generate_transactions(accounts, profiles):
    transactions = []
    tid = 1
    today = date.today()
    six_months_ago = today - timedelta(days=183)

    profile_by_cid = {p["customer_id"]: p for p in profiles}

    for acc in accounts:
        cid = acc["customer_id"]
        atype = acc["account_type"]
        profile = profile_by_cid.get(cid)
        monthly_income = profile["monthly_income"] if profile else 2000.0

        if atype == "current":
            employer = profile["employer_name"] if profile else "Employer"
            # Monthly salary credits
            for m in range(6):
                salary_date = today.replace(day=random.randint(25, 28)) - timedelta(days=30 * m)
                if salary_date < six_months_ago:
                    continue
                transactions.append({
                    "transaction_id": f"T{tid:05d}",
                    "account_id": acc["account_id"],
                    "description": f"Salary - {employer}",
                    "amount": round(monthly_income * random.uniform(0.95, 1.0), 2),
                    "type": "credit",
                    "category": "income",
                    "date": fmt(salary_date),
                })
                tid += 1

            # Monthly debit transactions
            life_stage = profile.get("employment_type", "full-time") if profile else "full-time"
            for m in range(6):
                month_start = today - timedelta(days=30 * (m + 1))
                # Groceries (2-4 per month)
                for _ in range(random.randint(2, 4)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["groceries"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "groceries", "date": fmt(txn_date),
                    })
                    tid += 1
                # Transport (2-6/month)
                for _ in range(random.randint(2, 6)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["transport"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "transport", "date": fmt(txn_date),
                    })
                    tid += 1
                # Dining (1-4/month)
                for _ in range(random.randint(1, 4)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["dining"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "dining", "date": fmt(txn_date),
                    })
                    tid += 1
                # Food delivery (0-2/month)
                for _ in range(random.randint(0, 2)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["food_delivery"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "food_delivery", "date": fmt(txn_date),
                    })
                    tid += 1
                # Utilities (1/month each)
                for _ in range(1):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["utilities"])
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "utilities",
                        "date": fmt(month_start + timedelta(days=random.randint(1, 5))),
                    })
                    tid += 1
                # Energy (1/month)
                merchant, lo, hi = random.choice(DEBIT_MERCHANTS["energy"])
                transactions.append({
                    "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                    "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                    "type": "debit", "category": "energy",
                    "date": fmt(month_start + timedelta(days=random.randint(1, 5))),
                })
                tid += 1
                # Entertainment (1-2/month)
                for _ in range(random.randint(1, 2)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["entertainment"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "entertainment", "date": fmt(txn_date),
                    })
                    tid += 1
                # Shopping (0-3/month)
                for _ in range(random.randint(0, 3)):
                    merchant, lo, hi = random.choice(DEBIT_MERCHANTS["shopping"])
                    txn_date = rdate(month_start, month_start + timedelta(days=28))
                    if txn_date < six_months_ago: continue
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": merchant, "amount": round(random.uniform(lo, hi), 2),
                        "type": "debit", "category": "shopping", "date": fmt(txn_date),
                    })
                    tid += 1
                # Rent (monthly, for ~60% of non-homeowners)
                if random.random() < 0.55:
                    rent_lo, rent_hi = DEBIT_MERCHANTS["housing"][0][1], DEBIT_MERCHANTS["housing"][0][2]
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": "Rent Payment", "amount": round(random.uniform(rent_lo, rent_hi), 2),
                        "type": "debit", "category": "housing",
                        "date": fmt(month_start + timedelta(days=1)),
                    })
                    tid += 1
                # Savings transfer (monthly)
                if random.random() < 0.6:
                    sav_lo, sav_hi = DEBIT_MERCHANTS["transfers"][0][1], DEBIT_MERCHANTS["transfers"][0][2]
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": "Transfer to Savings", "amount": round(random.uniform(sav_lo, sav_hi), 2),
                        "type": "debit", "category": "transfer",
                        "date": fmt(month_start + timedelta(days=random.randint(28, 30))),
                    })
                    tid += 1

        elif atype in ("savings", "isa"):
            # Monthly interest credits + incoming transfers
            interest_rate = acc["interest_rate"] / 100 / 12
            monthly_interest = round(acc["balance"] * interest_rate, 2)
            for m in range(6):
                int_date = (today.replace(day=1) - timedelta(days=30 * m))
                transactions.append({
                    "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                    "description": "Interest Credit", "amount": max(0.01, monthly_interest),
                    "type": "credit", "category": "interest", "date": fmt(int_date),
                })
                tid += 1
                # Monthly savings deposit
                if random.random() < 0.7:
                    dep_amount = round(random.uniform(100, min(600, acc["balance"] * 0.1)), 2)
                    transactions.append({
                        "transaction_id": f"T{tid:05d}", "account_id": acc["account_id"],
                        "description": "Transfer from Current Account",
                        "amount": dep_amount, "type": "credit", "category": "transfer",
                        "date": fmt(int_date + timedelta(days=random.randint(1, 5))),
                    })
                    tid += 1

    return transactions


# ── Loans generation ──────────────────────────────────────────────────────────

def generate_loans(customers, profiles):
    loans = []
    lid = 1
    today = date.today()
    profile_by_cid = {p["customer_id"]: p for p in profiles}

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        profile = profile_by_cid.get(cid)
        if not profile: continue

        monthly_income = profile["monthly_income"]
        has_loan_pct = LIFE_STAGE_PROFILES.get(life_stage, {}).get("has_loan_pct", 0)

        # Mortgage for family/pre_retirement with higher income
        if life_stage in ("family", "pre_retirement") and monthly_income > 2500 and random.random() < 0.5:
            principal = round(random.uniform(120000, 450000) / 1000) * 1000
            rate = round(random.uniform(3.5, 5.5), 2)
            tenure = random.choice([240, 300, 360])
            started = rdate(date(today.year - random.randint(3, 18), 1, 1),
                            date(today.year - 1, 12, 31))
            months_passed = (today.year - started.year) * 12 + (today.month - started.month)
            remaining = max(12, tenure - months_passed)
            monthly_rate = rate / 100 / 12
            emi = round(principal * monthly_rate * (1 + monthly_rate)**tenure /
                        ((1 + monthly_rate)**tenure - 1), 2)
            outstanding = round(emi * remaining, 2)
            lender = random.choice(LLOYDS_MORTGAGE_LENDERS)
            loans.append({
                "loan_id": f"LN{lid:04d}", "customer_id": cid,
                "loan_type": "mortgage", "lender_name": lender,
                "principal_amount": float(principal), "outstanding_amount": float(outstanding),
                "interest_rate": rate, "emi": emi,
                "tenure_months": tenure, "remaining_months": remaining,
                "start_date": fmt(started), "end_date": fmt(started + timedelta(days=tenure * 30.5)),
                "status": "active",
            })
            lid += 1

        # Personal / car / home improvement loan
        if random.random() < has_loan_pct:
            loan_type_data = random.choice(LLOYDS_LOAN_TYPES)
            lname, lrate, tmin, tmax = loan_type_data
            principal = round(random.uniform(3000, 25000) / 500) * 500
            tenure = random.randint(tmin, tmax)
            started = rdate(date(today.year - 3, 1, 1), today)
            months_passed = (today.year - started.year) * 12 + (today.month - started.month)
            remaining = max(1, tenure - months_passed)
            monthly_rate = lrate / 100 / 12
            emi = round(principal * monthly_rate * (1 + monthly_rate)**tenure /
                        ((1 + monthly_rate)**tenure - 1), 2)
            outstanding = round(emi * remaining, 2)
            loans.append({
                "loan_id": f"LN{lid:04d}", "customer_id": cid,
                "loan_type": lname.lower().replace(" ", "_"), "lender_name": "Lloyds Bank",
                "principal_amount": float(principal), "outstanding_amount": float(outstanding),
                "interest_rate": lrate, "emi": emi,
                "tenure_months": tenure, "remaining_months": remaining,
                "start_date": fmt(started), "end_date": fmt(started + timedelta(days=tenure * 30.5)),
                "status": "active",
            })
            lid += 1

    return loans


# ── Credit cards ──────────────────────────────────────────────────────────────

def generate_credit_cards(customers, profiles):
    cards = []
    ccid = 1
    today = date.today()
    profile_by_cid = {p["customer_id"]: p for p in profiles}

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        profile = profile_by_cid.get(cid)
        if not profile: continue

        has_cc_pct = LIFE_STAGE_PROFILES.get(life_stage, {}).get("has_cc_pct", 0)
        if random.random() > has_cc_pct: continue

        card_name, apr, max_limit, monthly_rate = random.choice(LLOYDS_CREDIT_CARDS)
        monthly_income = profile["monthly_income"]
        credit_limit = min(max_limit, round(monthly_income * random.uniform(2, 5) / 500) * 500)
        utilisation = random.uniform(0.05, 0.7)
        outstanding = round(credit_limit * utilisation, 2)
        min_due = round(max(25.0, outstanding * 0.02), 2)
        due_date = (today + timedelta(days=random.randint(7, 21))).isoformat()

        cards.append({
            "card_id": f"CC{ccid:04d}", "customer_id": cid,
            "card_name": card_name, "issuer": "Lloyds Bank",
            "credit_limit": float(credit_limit),
            "current_outstanding": float(outstanding),
            "minimum_due": float(min_due),
            "payment_due_date": due_date,
            "interest_rate": monthly_rate,
            "status": "active",
        })
        ccid += 1

    return cards


# ── Investments ───────────────────────────────────────────────────────────────

def generate_investments(customers, profiles):
    investments = []
    invid = 1
    today = date.today()
    profile_by_cid = {p["customer_id"]: p for p in profiles}

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        profile = profile_by_cid.get(cid)
        if not profile or life_stage in ("student", "child"): continue

        if random.random() > 0.45: continue

        n_investments = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        risk_appetite = profile.get("risk_appetite", "moderate")
        eligible = [a for a in INVESTMENT_ASSETS
                    if (risk_appetite == "conservative" and a[4] == "low") or
                       (risk_appetite == "moderate" and a[4] in ("low", "medium")) or
                       (risk_appetite == "aggressive")]
        if not eligible:
            eligible = INVESTMENT_ASSETS

        chosen = random.sample(eligible, min(n_investments, len(eligible)))
        for asset in chosen:
            name, atype, category, annual_return, risk = asset
            started = rdate(date(today.year - random.randint(1, 8), 4, 6), today)
            invested = round(random.uniform(1000, 30000) / 100) * 100
            months = (today.year - started.year) * 12 + (today.month - started.month)
            growth = (1 + annual_return / 12) ** months
            current_value = round(invested * growth, 2)
            monthly_sip = round(random.choice([0.0, 0.0, 100.0, 200.0, 300.0, 500.0]), 2)

            investments.append({
                "investment_id": f"INV{invid:04d}", "customer_id": cid,
                "asset_type": atype, "asset_name": name,
                "invested_amount": float(invested),
                "current_value": float(current_value),
                "monthly_sip": monthly_sip,
                "risk_level": risk,
                "category": category,
                "purchase_date": fmt(started),
                "status": "active",
            })
            invid += 1

    return investments


# ── Fixed deposits ────────────────────────────────────────────────────────────

def generate_fixed_deposits(customers, profiles):
    fds = []
    fdid = 1
    today = date.today()
    profile_by_cid = {p["customer_id"]: p for p in profiles}

    FD_PRODUCTS = [
        ("Lloyds Bank Fixed Rate Saver 1 Year", 4.50, 12),
        ("Lloyds Bank Fixed Rate Saver 2 Year", 4.25, 24),
        ("Lloyds Bank Fixed Rate Saver 3 Year", 4.10, 36),
    ]

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        profile = profile_by_cid.get(cid)
        if not profile or life_stage in ("student", "child"): continue

        if life_stage in ("pre_retirement", "retired"):
            pct = 0.6
        elif life_stage == "family":
            pct = 0.3
        else:
            pct = 0.15

        if random.random() > pct: continue

        name, rate, months = random.choice(FD_PRODUCTS)
        principal = round(random.uniform(2000, 50000) / 1000) * 1000
        started = rdate(date(today.year - 2, 1, 1), today)
        maturity = started + timedelta(days=months * 30.5)
        maturity_amount = round(principal * (1 + rate / 100 * months / 12), 2)
        status = "matured" if maturity < today else "active"

        fds.append({
            "fd_id": f"FD{fdid:04d}", "customer_id": cid,
            "bank_name": "Lloyds Bank",
            "principal_amount": float(principal),
            "interest_rate": rate,
            "maturity_amount": float(maturity_amount),
            "start_date": fmt(started), "maturity_date": fmt(maturity),
            "tenure_months": months,
            "status": status,
        })
        fdid += 1

    return fds


# ── Insurance ─────────────────────────────────────────────────────────────────

def generate_insurance(customers, profiles):
    policies = []
    polid = 1
    today = date.today()
    profile_by_cid = {p["customer_id"]: p for p in profiles}

    for cust in customers:
        cid = cust["customer_id"]
        life_stage = cust["life_stage"]
        profile = profile_by_cid.get(cid)
        if not profile or life_stage in ("student", "child"): continue

        monthly_income = profile["monthly_income"]

        for pol_type, pol_name, insurer, min_assured, max_assured, (prem_lo, prem_hi) in INSURANCE_PRODUCTS:
            take_up = {
                "home_buildings": 0.5 if life_stage in ("family", "pre_retirement", "retired") else 0.1,
                "home_contents": 0.6,
                "life": 0.45 if life_stage in ("family", "pre_retirement") else 0.2,
                "critical_illness": 0.3,
                "income_protection": 0.25,
                "car": 0.55,
                "health": 0.2,
            }.get(pol_type, 0.2)

            if random.random() > take_up: continue

            assured = round(random.uniform(min_assured, max_assured) / 10000) * 10000
            premium = round(random.uniform(prem_lo, prem_hi), 2)
            started = rdate(date(today.year - random.randint(0, 5), 1, 1), today)
            end = started + timedelta(days=365)

            policies.append({
                "policy_id": f"POL{polid:04d}", "customer_id": cid,
                "policy_type": pol_type, "policy_name": pol_name,
                "insurer": insurer, "sum_assured": float(assured),
                "premium": float(premium), "frequency": "annual",
                "start_date": fmt(started), "end_date": fmt(end),
                "nominee": random.choice(["Spouse", "Parent", "Child", "Partner", "Self"]),
                "status": "active",
            })
            polid += 1

    return policies


# ── Merchant categories (UK) ──────────────────────────────────────────────────

def merchant_categories():
    return [
        {"merchant_id": "M001", "merchant_pattern": "TESCO|SAINSBURY|ASDA|MORRISONS|WAITROSE|LIDL|ALDI|OCADO|CO-OP FOOD|M&S FOOD|ICELAND",
         "merchant_name": "Supermarkets", "category": "Groceries", "subcategory": "supermarket", "is_essential": True},
        {"merchant_id": "M002", "merchant_pattern": "AMAZON|ASOS|NEXT|JOHN LEWIS|ARGOS|CURRYS|PRIMARK|H&M|EBAY|MARKS & SPENCER",
         "merchant_name": "Online & Retail Shopping", "category": "Shopping", "subcategory": "retail", "is_essential": False},
        {"merchant_id": "M003", "merchant_pattern": "TFL OYSTER|NATIONAL RAIL|TRAINLINE|UBER|BP PETROL|SHELL PETROL|ESSO|JET2",
         "merchant_name": "Transport", "category": "Transport", "subcategory": "travel", "is_essential": True},
        {"merchant_id": "M004", "merchant_pattern": "PRET A MANGER|COSTA COFFEE|GREGGS|MCDONALD|NANDO|WAGAMAMA|PIZZA EXPRESS|WETHERSPOON",
         "merchant_name": "Cafes & Restaurants", "category": "Dining Out", "subcategory": "eating_out", "is_essential": False},
        {"merchant_id": "M005", "merchant_pattern": "DELIVEROO|JUST EAT|UBER EATS",
         "merchant_name": "Food Delivery", "category": "Food Delivery", "subcategory": "delivery", "is_essential": False},
        {"merchant_id": "M006", "merchant_pattern": "BT BROADBAND|SKY TV|VIRGIN MEDIA|EE MOBILE|O2 MOBILE|VODAFONE UK|THREE MOBILE|GIFFGAFF",
         "merchant_name": "Telecoms", "category": "Utilities", "subcategory": "telecoms", "is_essential": True},
        {"merchant_id": "M007", "merchant_pattern": "BRITISH GAS|EDF ENERGY|OCTOPUS ENERGY|E.ON ENERGY|SCOTTISH POWER",
         "merchant_name": "Energy", "category": "Energy", "subcategory": "utilities", "is_essential": True},
        {"merchant_id": "M008", "merchant_pattern": "NETFLIX|SPOTIFY|DISNEY|AMAZON PRIME|SKY SPORTS|ODEON|VUE CINEMA",
         "merchant_name": "Streaming & Entertainment", "category": "Entertainment", "subcategory": "leisure", "is_essential": False},
        {"merchant_id": "M009", "merchant_pattern": "NHS PRESCRIPTION|SPECSAVERS|DENTAL PRACTICE|BUPA|PHARMACY|BOOTS|SUPERDRUG",
         "merchant_name": "Health & Pharmacy", "category": "Healthcare", "subcategory": "health", "is_essential": True},
        {"merchant_id": "M010", "merchant_pattern": "RENT PAYMENT|MORTGAGE",
         "merchant_name": "Housing", "category": "Housing", "subcategory": "accommodation", "is_essential": True},
        {"merchant_id": "M011", "merchant_pattern": "CAR INSURANCE|HOME INSURANCE|LIFE INSURANCE|PET INSURANCE",
         "merchant_name": "Insurance", "category": "Insurance", "subcategory": "protection", "is_essential": True},
        {"merchant_id": "M012", "merchant_pattern": "PUREGYM|THE GYM GROUP|FITNESS",
         "merchant_name": "Gym & Fitness", "category": "Health & Fitness", "subcategory": "fitness", "is_essential": False},
        {"merchant_id": "M013", "merchant_pattern": "TRANSFER TO SAVINGS|SAVINGS TRANSFER",
         "merchant_name": "Savings Transfer", "category": "Savings", "subcategory": "transfer", "is_essential": True},
        {"merchant_id": "M014", "merchant_pattern": "INTEREST CREDIT|BANK INTEREST",
         "merchant_name": "Interest", "category": "Interest", "subcategory": "bank_interest", "is_essential": False},
        {"merchant_id": "M015", "merchant_pattern": "SALARY|WAGES|EMPLOYER",
         "merchant_name": "Salary/Wages", "category": "Income", "subcategory": "employment_income", "is_essential": False},
    ]


# ── Products table (Lloyds products) ─────────────────────────────────────────

def generate_products():
    products = []
    pid = 1

    # Current accounts
    for name, fee, _ , _ in LLOYDS_CURRENT_ACCOUNTS:
        features_map = {
            "Classic Current Account": "Free banking, contactless card, mobile app, overdraft facility",
            "Club Lloyds Current Account": "Monthly reward, enhanced savings rates, cinema tickets, magazine subscription",
            "Silver Current Account": "AA Breakdown Cover, European travel insurance, mobile phone insurance",
            "Gold Current Account": "Worldwide travel insurance, mobile phone insurance, AA Breakdown Cover",
            "Platinum Current Account": "Worldwide family travel insurance, mobile phone insurance, AA Breakdown, home emergency",
            "Student Current Account": "Fee-free overdraft up to £1,500, cashback offers, no monthly fee",
            "Graduate Current Account": "Fee-free overdraft up to £2,000, cashback offers, builds credit history",
        }
        segment_map = {
            "Classic Current Account": "adults",
            "Club Lloyds Current Account": "adults",
            "Silver Current Account": "adults",
            "Gold Current Account": "adults",
            "Platinum Current Account": "adults",
            "Student Current Account": "students_18_plus",
            "Graduate Current Account": "graduates_21_28",
        }
        products.append({
            "product_id": f"P{pid:03d}", "product_name": name,
            "product_type": "current",
            "interest_rate_pa": 0.10 if "Club Lloyds" in name else 0.0,
            "monthly_fee": fee,
            "min_deposit": 0.0, "max_balance": 1000000.0,
            "access_type": "instant", "notice_period_days": 0, "term_months": 0,
            "features": features_map.get(name, "Standard banking features"),
            "target_segment": segment_map.get(name, "adults"),
            "min_age": 18, "is_active": True,
        })
        pid += 1

    # Savings accounts
    savings_details = [
        ("Easy Saver", "savings", 1.20, 0.0, 1.0, 250000.0, "instant", 0, 0,
         "Instant access, no notice required, open online or in branch", "adults", 18),
        ("Club Lloyds Monthly Saver", "savings", 6.25, 0.0, 25.0, 4800.0, "notice", 0, 12,
         "Fixed rate for 12 months, pay in £25-£400/month, requires Club Lloyds", "club_lloyds_customers", 18),
        ("Cash ISA", "isa", 4.15, 0.0, 1.0, 20000.0, "instant", 0, 0,
         "Tax-free savings up to £20,000/year, instant access, flexible", "adults", 18),
        ("Fixed Rate Saver 1 Year", "savings", 4.50, 0.0, 2000.0, 5000000.0, "fixed", 0, 12,
         "Fixed rate for 12 months, min deposit £2,000, guaranteed return", "adults", 18),
        ("Fixed Rate Saver 2 Year", "savings", 4.25, 0.0, 2000.0, 5000000.0, "fixed", 0, 24,
         "Fixed rate for 24 months, min deposit £2,000, guaranteed return", "adults", 18),
        ("Fixed Rate Saver 3 Year", "savings", 4.10, 0.0, 2000.0, 5000000.0, "fixed", 0, 36,
         "Fixed rate for 36 months, min deposit £2,000, guaranteed return", "adults", 18),
        ("Junior Cash ISA", "isa", 3.75, 0.0, 1.0, 9000.0, "fixed", 0, 0,
         "Tax-free savings for under 18s, up to £9,000/year, managed by parent/guardian", "children_under_18", 0),
        ("Children's Saver", "savings", 3.25, 0.0, 1.0, 1200.0, "instant", 0, 0,
         "Savings account for under 16s, max £100/month, instant access", "children_under_16", 0),
    ]
    for name, ptype, rate, fee, min_d, max_d, access, notice, term, features, segment, min_age in savings_details:
        products.append({
            "product_id": f"P{pid:03d}", "product_name": name,
            "product_type": ptype, "interest_rate_pa": rate,
            "monthly_fee": fee, "min_deposit": min_d, "max_balance": max_d,
            "access_type": access, "notice_period_days": notice, "term_months": term,
            "features": features, "target_segment": segment,
            "min_age": min_age, "is_active": True,
        })
        pid += 1

    return products


# ── BigQuery upload ───────────────────────────────────────────────────────────

SCHEMAS = {
    "customers": [
        bigquery.SchemaField("customer_id",        "STRING"),
        bigquery.SchemaField("name",               "STRING"),
        bigquery.SchemaField("dob",                "STRING"),
        bigquery.SchemaField("postcode",           "STRING"),
        bigquery.SchemaField("address",            "STRING"),
        bigquery.SchemaField("age",                "INTEGER"),
        bigquery.SchemaField("gender",             "STRING"),
        bigquery.SchemaField("phone",              "STRING"),
        bigquery.SchemaField("email",              "STRING"),
        bigquery.SchemaField("occupation",         "STRING"),
        bigquery.SchemaField("annual_income_band", "STRING"),
        bigquery.SchemaField("life_stage",         "STRING"),
    ],
    "accounts": [
        bigquery.SchemaField("account_id",    "STRING"),
        bigquery.SchemaField("customer_id",   "STRING"),
        bigquery.SchemaField("product_type",  "STRING"),
        bigquery.SchemaField("account_type",  "STRING"),
        bigquery.SchemaField("opened_date",   "STRING"),
        bigquery.SchemaField("balance",       "FLOAT"),
        bigquery.SchemaField("interest_rate", "FLOAT"),
    ],
    "transactions": [
        bigquery.SchemaField("transaction_id", "STRING"),
        bigquery.SchemaField("account_id",     "STRING"),
        bigquery.SchemaField("description",    "STRING"),
        bigquery.SchemaField("amount",         "FLOAT"),
        bigquery.SchemaField("type",           "STRING"),
        bigquery.SchemaField("category",       "STRING"),
        bigquery.SchemaField("date",           "STRING"),
    ],
    "customer_profile": [
        bigquery.SchemaField("profile_id",           "STRING"),
        bigquery.SchemaField("customer_id",          "STRING"),
        bigquery.SchemaField("monthly_income",       "FLOAT"),
        bigquery.SchemaField("employment_type",      "STRING"),
        bigquery.SchemaField("occupation",           "STRING"),
        bigquery.SchemaField("employer_name",        "STRING"),
        bigquery.SchemaField("marital_status",       "STRING"),
        bigquery.SchemaField("dependents",           "INTEGER"),
        bigquery.SchemaField("risk_appetite",        "STRING"),
        bigquery.SchemaField("investment_experience","STRING"),
        bigquery.SchemaField("preferred_language",   "STRING"),
        bigquery.SchemaField("financial_literacy",   "STRING"),
    ],
    "loans": [
        bigquery.SchemaField("loan_id",            "STRING"),
        bigquery.SchemaField("customer_id",        "STRING"),
        bigquery.SchemaField("loan_type",          "STRING"),
        bigquery.SchemaField("lender_name",        "STRING"),
        bigquery.SchemaField("principal_amount",   "FLOAT"),
        bigquery.SchemaField("outstanding_amount", "FLOAT"),
        bigquery.SchemaField("interest_rate",      "FLOAT"),
        bigquery.SchemaField("emi",                "FLOAT"),
        bigquery.SchemaField("tenure_months",      "INTEGER"),
        bigquery.SchemaField("remaining_months",   "INTEGER"),
        bigquery.SchemaField("start_date",         "STRING"),
        bigquery.SchemaField("end_date",           "STRING"),
        bigquery.SchemaField("status",             "STRING"),
    ],
    "credit_cards": [
        bigquery.SchemaField("card_id",             "STRING"),
        bigquery.SchemaField("customer_id",         "STRING"),
        bigquery.SchemaField("card_name",           "STRING"),
        bigquery.SchemaField("issuer",              "STRING"),
        bigquery.SchemaField("credit_limit",        "FLOAT"),
        bigquery.SchemaField("current_outstanding", "FLOAT"),
        bigquery.SchemaField("minimum_due",         "FLOAT"),
        bigquery.SchemaField("payment_due_date",    "STRING"),
        bigquery.SchemaField("interest_rate",       "FLOAT"),
        bigquery.SchemaField("status",              "STRING"),
    ],
    "investments": [
        bigquery.SchemaField("investment_id",    "STRING"),
        bigquery.SchemaField("customer_id",      "STRING"),
        bigquery.SchemaField("asset_type",       "STRING"),
        bigquery.SchemaField("asset_name",       "STRING"),
        bigquery.SchemaField("invested_amount",  "FLOAT"),
        bigquery.SchemaField("current_value",    "FLOAT"),
        bigquery.SchemaField("monthly_sip",      "FLOAT"),
        bigquery.SchemaField("risk_level",       "STRING"),
        bigquery.SchemaField("category",         "STRING"),
        bigquery.SchemaField("purchase_date",    "STRING"),
        bigquery.SchemaField("status",           "STRING"),
    ],
    "fixed_deposits": [
        bigquery.SchemaField("fd_id",             "STRING"),
        bigquery.SchemaField("customer_id",       "STRING"),
        bigquery.SchemaField("bank_name",         "STRING"),
        bigquery.SchemaField("principal_amount",  "FLOAT"),
        bigquery.SchemaField("interest_rate",     "FLOAT"),
        bigquery.SchemaField("maturity_amount",   "FLOAT"),
        bigquery.SchemaField("start_date",        "STRING"),
        bigquery.SchemaField("maturity_date",     "STRING"),
        bigquery.SchemaField("tenure_months",     "INTEGER"),
        bigquery.SchemaField("status",            "STRING"),
    ],
    "insurance": [
        bigquery.SchemaField("policy_id",    "STRING"),
        bigquery.SchemaField("customer_id",  "STRING"),
        bigquery.SchemaField("policy_type",  "STRING"),
        bigquery.SchemaField("policy_name",  "STRING"),
        bigquery.SchemaField("insurer",      "STRING"),
        bigquery.SchemaField("sum_assured",  "FLOAT"),
        bigquery.SchemaField("premium",      "FLOAT"),
        bigquery.SchemaField("frequency",    "STRING"),
        bigquery.SchemaField("start_date",   "STRING"),
        bigquery.SchemaField("end_date",     "STRING"),
        bigquery.SchemaField("nominee",      "STRING"),
        bigquery.SchemaField("status",       "STRING"),
    ],
    "merchant_categories": [
        bigquery.SchemaField("merchant_id",      "STRING"),
        bigquery.SchemaField("merchant_pattern", "STRING"),
        bigquery.SchemaField("merchant_name",    "STRING"),
        bigquery.SchemaField("category",         "STRING"),
        bigquery.SchemaField("subcategory",      "STRING"),
        bigquery.SchemaField("is_essential",     "BOOLEAN"),
    ],
    "products": [
        bigquery.SchemaField("product_id",         "STRING"),
        bigquery.SchemaField("product_name",       "STRING"),
        bigquery.SchemaField("product_type",       "STRING"),
        bigquery.SchemaField("interest_rate_pa",   "FLOAT"),
        bigquery.SchemaField("monthly_fee",        "FLOAT"),
        bigquery.SchemaField("min_deposit",        "FLOAT"),
        bigquery.SchemaField("max_balance",        "FLOAT"),
        bigquery.SchemaField("access_type",        "STRING"),
        bigquery.SchemaField("notice_period_days", "INTEGER"),
        bigquery.SchemaField("term_months",        "INTEGER"),
        bigquery.SchemaField("features",           "STRING"),
        bigquery.SchemaField("target_segment",     "STRING"),
        bigquery.SchemaField("min_age",            "INTEGER"),
        bigquery.SchemaField("is_active",          "BOOLEAN"),
    ],
}


def upload_table(client: bigquery.Client, table_name: str, rows: list) -> None:
    if not rows:
        print(f"  Skipping {table_name} — no rows")
        return
    table_ref = f"{PROJECT}.{DATASET}.{table_name}"
    schema = SCHEMAS[table_name]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    import json, io
    ndjson = "\n".join(json.dumps(r) for r in rows)
    job = client.load_table_from_file(
        io.BytesIO(ndjson.encode()),
        table_ref,
        job_config=job_config,
    )
    job.result()
    print(f"  {table_name:22s}: {len(rows):>6,} rows uploaded")


def main():
    client = bigquery.Client(project=PROJECT)
    print(f"\nSeeding BigQuery {PROJECT}.{DATASET} with UK Lloyds Banking data\n")

    print("Generating data...")
    customers, profiles = generate_customers(n_adults=200, n_children=30)
    accounts   = generate_accounts(customers)
    transactions = generate_transactions(accounts, profiles)
    loans      = generate_loans(customers, profiles)
    cards      = generate_credit_cards(customers, profiles)
    investments = generate_investments(customers, profiles)
    fds        = generate_fixed_deposits(customers, profiles)
    insurance  = generate_insurance(customers, profiles)
    merchant_cats = merchant_categories()
    products   = generate_products()

    print(f"  customers:           {len(customers):>5,}")
    print(f"  customer_profiles:   {len(profiles):>5,}")
    print(f"  accounts:            {len(accounts):>5,}")
    print(f"  transactions:        {len(transactions):>5,}")
    print(f"  loans:               {len(loans):>5,}")
    print(f"  credit_cards:        {len(cards):>5,}")
    print(f"  investments:         {len(investments):>5,}")
    print(f"  fixed_deposits:      {len(fds):>5,}")
    print(f"  insurance:           {len(insurance):>5,}")
    print(f"  merchant_categories: {len(merchant_cats):>5,}")
    print(f"  products:            {len(products):>5,}")

    print("\nUploading to BigQuery...")
    upload_table(client, "customers",           customers)
    upload_table(client, "customer_profile",    profiles)
    upload_table(client, "accounts",            accounts)
    upload_table(client, "transactions",        transactions)
    upload_table(client, "loans",               loans)
    upload_table(client, "credit_cards",        cards)
    upload_table(client, "investments",         investments)
    upload_table(client, "fixed_deposits",      fds)
    upload_table(client, "insurance",           insurance)
    upload_table(client, "merchant_categories", merchant_cats)
    upload_table(client, "products",            products)

    print("\nDone. All tables seeded with UK Lloyds Banking Group data.")
    print("Customer IDs: C001–C200 (adults), C201–C230 (children)")


if __name__ == "__main__":
    main()
