#!/usr/bin/env python3
"""
Inserts a single high-scoring test customer (C998) into all BANK_DATA tables.

Target score: ~93/100 across all 5 dimensions:
  Cash Flow & Savings (25/25): savings rate ~45%  → score 25
  Debt Health         (25/25): DTI ~5%, CC util ~6% → score 25
  Liquid Safety Net   (20/20): 11+ months cushion  → score 20
  Savings & Investments(13/20): wealth 1.3x income → score 13
  Insurance           (10/10): life + health        → score 10
  ──────────────────────────────────────────────────
  TOTAL ≈ 93/100 — Excellent

Run from ADKAgents root:
    uv run python bq_seed/seed_test_high_scorer.py
"""

import io
import json
from datetime import date, timedelta

from google.cloud import bigquery

PROJECT = "ltc-ipnihack-prj-11"
DATASET = "BANK_DATA"
CID = "C998"
TODAY = date.today()


def upsert(client, table_name, rows, schema):
    table_ref = f"{PROJECT}.{DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_APPEND",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    ndjson = "\n".join(json.dumps(r) for r in rows)
    job = client.load_table_from_file(
        io.BytesIO(ndjson.encode()), table_ref, job_config=job_config
    )
    job.result()
    print(f"  {table_name:<25}: +{len(rows)} row(s)")


def main():
    client = bigquery.Client(project=PROJECT)
    print(f"\nInserting high-scoring test customer {CID} into {PROJECT}.{DATASET}\n")

    # ── Customer ──────────────────────────────────────────────────────────────
    upsert(client, "customers", [{
        "customer_id": CID,
        "name":        "Emily Watson",
        "dob":         "1973-04-15",
        "postcode":    "SW1A 2AB",
        "address":     "14 Victoria Road, London",
        "age":         52,
        "gender":      "F",
        "phone":       "07712345998",
        "email":       "emily.watson998@gmail.com",
        "occupation":  "Software Architect",
        "annual_income_band": "80000-99999",
        "life_stage":  "pre_retirement",
    }], [
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
    ])

    # ── Customer Profile ──────────────────────────────────────────────────────
    upsert(client, "customer_profile", [{
        "profile_id":            "P998",
        "customer_id":           CID,
        "monthly_income":        7200.0,     # £7,200/month = £86,400/year
        "employment_type":       "full-time",
        "occupation":            "Software Architect",
        "employer_name":         "Accenture UK",
        "marital_status":        "married",
        "dependents":            1,
        "risk_appetite":         "moderate",
        "investment_experience": "intermediate",
        "preferred_language":    "en",
        "financial_literacy":    "advanced",
    }], [
        bigquery.SchemaField("profile_id",            "STRING"),
        bigquery.SchemaField("customer_id",           "STRING"),
        bigquery.SchemaField("monthly_income",        "FLOAT"),
        bigquery.SchemaField("employment_type",       "STRING"),
        bigquery.SchemaField("occupation",            "STRING"),
        bigquery.SchemaField("employer_name",         "STRING"),
        bigquery.SchemaField("marital_status",        "STRING"),
        bigquery.SchemaField("dependents",            "INTEGER"),
        bigquery.SchemaField("risk_appetite",         "STRING"),
        bigquery.SchemaField("investment_experience", "STRING"),
        bigquery.SchemaField("preferred_language",    "STRING"),
        bigquery.SchemaField("financial_literacy",    "STRING"),
    ])

    # ── Accounts ──────────────────────────────────────────────────────────────
    # Total bank balance = £28,500 → 28,500 / 2,100 spend ≈ 13.6 months cushion → 20/20
    upsert(client, "accounts", [
        {
            "account_id": "A9981", "customer_id": CID,
            "product_type": "Club Lloyds Current Account", "account_type": "current",
            "opened_date": "2015-03-10", "balance": 8500.0, "interest_rate": 0.10,
        },
        {
            "account_id": "A9982", "customer_id": CID,
            "product_type": "Cash ISA", "account_type": "isa",
            "opened_date": "2018-04-06", "balance": 20000.0, "interest_rate": 4.15,
        },
    ], [
        bigquery.SchemaField("account_id",    "STRING"),
        bigquery.SchemaField("customer_id",   "STRING"),
        bigquery.SchemaField("product_type",  "STRING"),
        bigquery.SchemaField("account_type",  "STRING"),
        bigquery.SchemaField("opened_date",   "STRING"),
        bigquery.SchemaField("balance",       "FLOAT"),
        bigquery.SchemaField("interest_rate", "FLOAT"),
    ])

    # ── Transactions: 6 months salary + realistic UK spend ───────────────────
    # Monthly credits: £7,200 salary
    # Monthly debits:  ~£2,100 (no rent — owns home; mortgage in loans table)
    # free_cash_flow = 7200 - 2100 - 300(EMI) - 40(CC_min) - 500(SIP) = £4,260
    # savings_rate = 4260 / 7200 = 59.2% → cash_flow_score = 25/25
    transactions = []
    tid = 9980

    monthly_debits = [
        # (description, amount, category)
        ("Salary - Accenture UK",           7200.00,  "income"),          # credit
        ("Waitrose & Partners",               95.00,   "groceries"),
        ("Waitrose & Partners",               88.00,   "groceries"),
        ("Waitrose & Partners",               72.00,   "groceries"),
        ("National Rail",                     145.00,  "transport"),
        ("Uber",                              22.00,   "transport"),
        ("Pret a Manger",                     8.50,    "dining"),
        ("Wagamama",                          38.00,   "dining"),
        ("Deliveroo",                         32.00,   "food_delivery"),
        ("Netflix",                           17.99,   "entertainment"),
        ("Spotify",                           9.99,    "entertainment"),
        ("PureGym",                           29.99,   "entertainment"),
        ("BT Broadband",                      48.00,   "utilities"),
        ("EE Mobile",                         42.00,   "utilities"),
        ("Octopus Energy",                    155.00,  "energy"),
        ("Amazon",                            88.00,   "shopping"),
        ("John Lewis",                        145.00,  "shopping"),
        ("Boots",                             22.00,   "healthcare"),
        ("NHS Prescription",                  9.90,    "healthcare"),
        ("Transfer to Savings",               500.00,  "transfer"),        # monthly save
    ]
    # total debits per month ≈ £1,523 non-salary + transfer

    for month in range(6):
        month_offset = 30 * month
        salary_date = (TODAY - timedelta(days=month_offset + 1)).replace(day=28)
        if salary_date > TODAY:
            salary_date = TODAY - timedelta(days=month_offset)

        for idx, (desc, amount, cat) in enumerate(monthly_debits):
            txn_date = salary_date - timedelta(days=idx % 28)
            if txn_date > TODAY:
                txn_date = TODAY
            is_salary = (cat == "income")
            transactions.append({
                "transaction_id": f"T{tid:05d}",
                "account_id":     "A9981",
                "description":    desc,
                "amount":         amount,
                "type":           "credit" if is_salary else "debit",
                "category":       cat,
                "date":           txn_date.isoformat(),
            })
            tid += 1

        # ISA monthly interest credit
        transactions.append({
            "transaction_id": f"T{tid:05d}",
            "account_id":     "A9982",
            "description":    "Interest Credit",
            "amount":         69.17,   # 20000 * 4.15% / 12
            "type":           "credit",
            "category":       "interest",
            "date":           (salary_date - timedelta(days=1)).isoformat(),
        })
        tid += 1

    upsert(client, "transactions", transactions, [
        bigquery.SchemaField("transaction_id", "STRING"),
        bigquery.SchemaField("account_id",     "STRING"),
        bigquery.SchemaField("description",    "STRING"),
        bigquery.SchemaField("amount",         "FLOAT"),
        bigquery.SchemaField("type",           "STRING"),
        bigquery.SchemaField("category",       "STRING"),
        bigquery.SchemaField("date",           "STRING"),
    ])

    # ── Loan: small home improvement loan ─────────────────────────────────────
    # EMI £300/month, outstanding £5,400 (18 months left)
    # DTI = (300 + 40) / 7200 = 4.7% → 25/25
    upsert(client, "loans", [{
        "loan_id":            "LN9981",
        "customer_id":        CID,
        "loan_type":          "home_improvement_loan",
        "lender_name":        "Lloyds Bank",
        "principal_amount":   12000.0,
        "outstanding_amount": 5400.0,
        "interest_rate":      7.9,
        "emi":                300.0,
        "tenure_months":      48,
        "remaining_months":   18,
        "start_date":         "2023-01-15",
        "end_date":           "2027-01-15",
        "status":             "active",
    }], [
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
    ])

    # ── Credit Card: low utilisation ──────────────────────────────────────────
    # £700 outstanding on £12,000 limit = 5.8% utilisation → no CC penalty
    # minimum_due £40
    due_date = (TODAY + timedelta(days=14)).isoformat()
    upsert(client, "credit_cards", [{
        "card_id":             "CC9981",
        "customer_id":         CID,
        "card_name":           "Lloyds Bank Platinum Mastercard",
        "issuer":              "Lloyds Bank",
        "credit_limit":        12000.0,
        "current_outstanding": 700.0,
        "minimum_due":         40.0,
        "payment_due_date":    due_date,
        "interest_rate":       3.59,
        "status":              "active",
    }], [
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
    ])

    # ── Investments ───────────────────────────────────────────────────────────
    # total wealth = 60,000 + 42,000 = 102,000
    # wealth_to_income = 102,000 / (7200*12) = 102,000/86,400 = 1.18x → 11.8/20
    upsert(client, "investments", [
        {
            "investment_id": "INV9981", "customer_id": CID,
            "asset_type":    "index_fund",
            "asset_name":    "FTSE 100 Tracker",
            "invested_amount":  45000.0,
            "current_value":    58500.0,     # +30% gain over 6 years
            "monthly_sip":      300.0,
            "risk_level":       "medium",
            "category":         "equity",
            "purchase_date":    "2019-04-06",
            "status":           "active",
        },
        {
            "investment_id": "INV9982", "customer_id": CID,
            "asset_type":    "isa",
            "asset_name":    "Stocks and Shares ISA",
            "invested_amount":  18000.0,
            "current_value":    21600.0,     # +20% gain over 3 years
            "monthly_sip":      200.0,
            "risk_level":       "medium",
            "category":         "equity",
            "purchase_date":    "2022-04-06",
            "status":           "active",
        },
    ], [
        bigquery.SchemaField("investment_id",   "STRING"),
        bigquery.SchemaField("customer_id",     "STRING"),
        bigquery.SchemaField("asset_type",      "STRING"),
        bigquery.SchemaField("asset_name",      "STRING"),
        bigquery.SchemaField("invested_amount", "FLOAT"),
        bigquery.SchemaField("current_value",   "FLOAT"),
        bigquery.SchemaField("monthly_sip",     "FLOAT"),
        bigquery.SchemaField("risk_level",      "STRING"),
        bigquery.SchemaField("category",        "STRING"),
        bigquery.SchemaField("purchase_date",   "STRING"),
        bigquery.SchemaField("status",          "STRING"),
    ])

    # ── Fixed Deposit ─────────────────────────────────────────────────────────
    # £42,000 FD → total_wealth = 80,100 + 42,000 = 122,100
    # wealth_to_income = 122,100 / 86,400 = 1.41x → 14.1/20
    upsert(client, "fixed_deposits", [{
        "fd_id":            "FD9981",
        "customer_id":      CID,
        "bank_name":        "Lloyds Bank",
        "principal_amount": 42000.0,
        "interest_rate":    4.25,
        "maturity_amount":  45570.0,    # 42000 × (1 + 4.25%×2)
        "start_date":       "2024-03-01",
        "maturity_date":    "2026-03-01",
        "tenure_months":    24,
        "status":           "active",
    }], [
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
    ])

    # ── Insurance: life + health = 10/10 ─────────────────────────────────────
    upsert(client, "insurance", [
        {
            "policy_id":   "POL9981", "customer_id": CID,
            "policy_type": "life",
            "policy_name": "Lloyds Bank Level Term Life",
            "insurer":     "Scottish Widows",
            "sum_assured": 300000.0,
            "premium":     45.0,
            "frequency":   "annual",
            "start_date":  "2020-01-01",
            "end_date":    "2035-01-01",
            "nominee":     "Spouse",
            "status":      "active",
        },
        {
            "policy_id":   "POL9982", "customer_id": CID,
            "policy_type": "health",
            "policy_name": "Lloyds Bank Health Cover",
            "insurer":     "Bupa",
            "sum_assured": 50000.0,
            "premium":     120.0,
            "frequency":   "annual",
            "start_date":  "2021-06-01",
            "end_date":    "2027-06-01",
            "nominee":     "Self",
            "status":      "active",
        },
        {
            "policy_id":   "POL9983", "customer_id": CID,
            "policy_type": "home_buildings",
            "policy_name": "Lloyds Bank Home Insurance",
            "insurer":     "Lloyds Bank Insurance",
            "sum_assured": 450000.0,
            "premium":     280.0,
            "frequency":   "annual",
            "start_date":  "2024-01-01",
            "end_date":    "2025-01-01",
            "nominee":     "Self",
            "status":      "active",
        },
    ], [
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
    ])

    # ── Expected score preview ────────────────────────────────────────────────
    monthly_income   = 7200.0
    monthly_spend    = sum(a for d, a, c in monthly_debits if c != "income" and c != "transfer")
    total_emi        = 300.0
    cc_min           = 40.0
    total_sip        = 500.0   # monthly_sip 300+200 from investments
    free_cf          = monthly_income - monthly_spend - total_emi - cc_min - total_sip
    savings_rate     = free_cf / monthly_income * 100
    cf_score         = min(25, savings_rate / 20 * 25)

    dti              = (total_emi + cc_min) / monthly_income * 100
    dti_score        = 25 if dti < 20 else 18 if dti < 30 else 12
    cc_util          = 700 / 12000 * 100
    cc_penalty       = max(0, (cc_util - 30) / 70 * 5) if cc_util > 30 else 0
    debt_score       = round(dti_score - cc_penalty, 1)

    bank_balance     = 8500 + 20000
    cushion          = bank_balance / monthly_spend
    cushion_score    = min(20, cushion / 6 * 20)

    inv_value        = 58500 + 21600
    total_fd         = 42000
    wealth           = inv_value + total_fd
    annual_income    = monthly_income * 12
    w2i              = wealth / annual_income
    inv_score        = min(20, w2i / 2 * 20)

    ins_score        = 10  # has life + health

    total            = round(cf_score + debt_score + cushion_score + inv_score + ins_score, 1)

    print(f"\nExpected score for {CID} (Emily Watson):")
    print(f"  Monthly income:       £{monthly_income:,.0f}")
    print(f"  Monthly spend:        £{monthly_spend:,.2f}")
    print(f"  Free cash flow:       £{free_cf:,.2f}  ({savings_rate:.1f}% savings rate)")
    print(f"  Cash Flow score:      {cf_score:.1f}/25")
    print(f"  DTI:                  {dti:.1f}%  → Debt score: {debt_score}/25")
    print(f"  Bank balance:         £{bank_balance:,.0f}  ({cushion:.1f} months cushion)")
    print(f"  Cushion score:        {cushion_score:.1f}/20")
    print(f"  Wealth:               £{wealth:,.0f}  ({w2i:.2f}x annual income)")
    print(f"  Investment score:     {inv_score:.1f}/20")
    print(f"  Insurance score:      {ins_score}/10")
    print(f"  ──────────────────────────────")
    print(f"  TOTAL:                {total}/100")
    print(f"\nTest with customer ID: {CID}  (name: Emily Watson)")


if __name__ == "__main__":
    main()
