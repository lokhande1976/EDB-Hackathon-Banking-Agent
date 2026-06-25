import os
import sqlite3
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from google.adk.tools.tool_context import ToolContext
from google.cloud import bigquery

from ..observability.tool_tracer import traced_tool

load_dotenv()

BQ_DATASET = os.getenv("BQ_DATASET", "")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")


@lru_cache(maxsize=1)
def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)


@traced_tool
def customer_id_search(customer_id: str, tool_context: ToolContext) -> dict:
    """Retrieves customer information for a particular customer ID, used for verifying identity.

    Args:
        customer_id (str): The customer ID for the customer who to verify
        tool_context: provides the state of verification

    Returns:
        dict: status and result or error msg.
    """
    try:
        customer_id = customer_id.strip().upper()
        # SECURITY CHECK: Ensure identity is verified
        if tool_context.state.get("identity_verified") and customer_id != tool_context.state.get("verified_customer_id"):
            tool_context.state["verified_customer_id"] = ""
            tool_context.state["identity_verified"] = False
            return {"status": "error", "error_message": "Customer identity is not the same as verified. Verify the customer again"}
        elif tool_context.state.get("identity_verified") and customer_id == tool_context.state.get("verified_customer_id"):
            verified_id = tool_context.state.get("verified_customer_id")
        else:
            tool_context.state["identity_verified"] = False
            verified_id = customer_id

        print(f"Customer ID searched: {verified_id}")

        if BQ_DATASET:
            print("Pulling customer details from BigQuery")
            client = _bq_client()
            query = f"""
                SELECT customer_id, name, dob, postcode
                FROM `{BQ_DATASET}.customers`
                WHERE customer_id = @customer_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("customer_id", "STRING", verified_id)]
            )
            result_df = client.query(query, job_config=job_config).to_dataframe()

            if result_df.empty:
                return {"status": "error", "error_message": "no values returned for customer ID"}

            result = result_df.iloc[0].to_dict()
        else:
            conn = sqlite3.connect("bank_data.db")
            query = """
                SELECT customer_id, name, dob, postcode
                FROM customers
                WHERE customer_id = ?
            """
            result_df = pd.read_sql_query(query, conn, params=[verified_id])
            conn.close()

            if result_df.empty:
                return {"status": "error", "error_message": "no values returned for customer ID"}

            result = result_df.iloc[0].to_dict()

        tool_context.state["identity_verified"] = True
        tool_context.state["verified_customer_id"] = verified_id
        result["status"] = "success"
        return result

    except Exception as e:
        return {"status": "error", "error_message": f"Database Error: {str(e)}"}


@traced_tool
def customer_database_search(tool_context: ToolContext) -> str:
    """
    Retrieves the currently verified customer's profile and recent financial activity.
    This tool requires no arguments as it uses the ID from the verified session context.
    tool_context: provides the state of verification
    """
    try:
        if not tool_context.state.get("identity_verified"):
            return "ERROR: Customer identity has not been verified. Please verify the customer before searching records."

        verified_id = tool_context.state.get("verified_customer_id")

        if not verified_id:
            return "ERROR: Session error. Identity verified but no Customer ID found in context."

        cache_key = f"bq_profile_{verified_id}"
        cached = tool_context.state.get(cache_key)
        if cached:
            print(f"Cache hit: customer profile for {verified_id}")
            return cached

        if BQ_DATASET:
            print("Pulling comprehensive customer profile from BigQuery")
            client = _bq_client()

            # Run all sub-queries in a single multi-CTE query
            query = f"""
                WITH cust AS (
                    SELECT customer_id, name, dob, postcode, address, age, gender, phone, email,
                           occupation, annual_income_band, life_stage
                    FROM `{BQ_DATASET}.customers`
                    WHERE customer_id = @cid
                ),
                prof AS (
                    SELECT monthly_income, employment_type, occupation, employer_name,
                           marital_status, dependents, risk_appetite,
                           investment_experience, financial_literacy
                    FROM `{BQ_DATASET}.customer_profile`
                    WHERE customer_id = @cid
                ),
                acct_rows AS (
                    SELECT product_type, ROUND(balance, 2) AS balance
                    FROM `{BQ_DATASET}.accounts`
                    WHERE customer_id = @cid
                ),
                loan_rows AS (
                    SELECT loan_type, lender_name,
                           ROUND(outstanding_amount, 0) AS outstanding,
                           ROUND(emi, 0) AS emi,
                           remaining_months, status
                    FROM `{BQ_DATASET}.loans`
                    WHERE customer_id = @cid
                ),
                cc_rows AS (
                    SELECT card_name, issuer,
                           ROUND(credit_limit, 0) AS credit_limit,
                           ROUND(current_outstanding, 0) AS outstanding,
                           ROUND(current_outstanding / NULLIF(credit_limit,0) * 100, 1) AS utilisation_pct,
                           status
                    FROM `{BQ_DATASET}.credit_cards`
                    WHERE customer_id = @cid
                ),
                inv_rows AS (
                    SELECT asset_type, asset_name,
                           ROUND(invested_amount, 0) AS invested,
                           ROUND(current_value, 0) AS current_value,
                           ROUND((current_value - invested_amount) / NULLIF(invested_amount,0) * 100, 1) AS gain_pct,
                           ROUND(monthly_sip, 0) AS monthly_sip,
                           risk_level, status
                    FROM `{BQ_DATASET}.investments`
                    WHERE customer_id = @cid
                ),
                fd_rows AS (
                    SELECT bank_name,
                           ROUND(principal_amount, 0) AS principal,
                           interest_rate,
                           ROUND(maturity_amount, 0) AS maturity_amount,
                           maturity_date, status
                    FROM `{BQ_DATASET}.fixed_deposits`
                    WHERE customer_id = @cid
                ),
                ins_rows AS (
                    SELECT policy_type, policy_name, insurer,
                           ROUND(sum_assured, 0) AS sum_assured,
                           ROUND(premium, 0) AS annual_premium,
                           end_date, status
                    FROM `{BQ_DATASET}.insurance`
                    WHERE customer_id = @cid
                ),
                recent_txns AS (
                    SELECT t.date, t.description,
                           ROUND(t.amount, 2) AS amount, t.type,
                           a.product_type AS account
                    FROM `{BQ_DATASET}.transactions` t
                    JOIN `{BQ_DATASET}.accounts` a ON t.account_id = a.account_id
                    WHERE a.customer_id = @cid
                    ORDER BY t.date DESC
                    LIMIT 20
                )
                SELECT
                  'customer' AS section,
                  TO_JSON_STRING((SELECT AS STRUCT * FROM cust LIMIT 1)) AS data
                UNION ALL SELECT 'profile', TO_JSON_STRING((SELECT AS STRUCT * FROM prof LIMIT 1))
                UNION ALL SELECT 'accounts', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM acct_rows))
                UNION ALL SELECT 'loans', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM loan_rows))
                UNION ALL SELECT 'credit_cards', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM cc_rows))
                UNION ALL SELECT 'investments', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM inv_rows))
                UNION ALL SELECT 'fixed_deposits', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM fd_rows))
                UNION ALL SELECT 'insurance', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM ins_rows))
                UNION ALL SELECT 'recent_transactions', TO_JSON_STRING(ARRAY(SELECT AS STRUCT * FROM recent_txns))
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("cid", "STRING", verified_id)]
            )
            rows_df = client.query(query, job_config=job_config).to_dataframe()
            if rows_df.empty:
                return "ERROR: No record found for this Customer ID."

            import json
            sections = {r["section"]: json.loads(r["data"]) for _, r in rows_df.iterrows()}

            def fmt_section(title: str, rows, fields: list[str]) -> str:
                if not rows:
                    return f"  None on record.\n"
                lines = []
                for row in (rows if isinstance(rows, list) else [rows]):
                    lines.append("  " + "  |  ".join(
                        f"{f}: {row.get(f, '')}" for f in fields if row.get(f) is not None
                    ))
                return "\n".join(lines) + "\n"

            cust = sections.get("customer", {})
            prof = sections.get("profile", {})
            result = f"""=== CUSTOMER PROFILE ===
  Name: {cust.get('name')}  |  ID: {cust.get('customer_id')}  |  Age: {cust.get('age')}  |  DOB: {cust.get('dob')}
  Postcode: {cust.get('postcode')}  |  Email: {cust.get('email')}  |  Phone: {cust.get('phone')}
  Address: {cust.get('address')}  |  Life Stage: {cust.get('life_stage')}  |  Occupation: {cust.get('occupation')}

=== FINANCIAL PROFILE ===
  Monthly Income: £{float(prof.get('monthly_income') or 0):,.0f}  |  Employment: {prof.get('employment_type')}  |  Occupation: {prof.get('occupation')} at {prof.get('employer_name')}
  Marital Status: {prof.get('marital_status')}  |  Dependents: {prof.get('dependents')}
  Risk Appetite: {prof.get('risk_appetite')}  |  Investment Experience: {prof.get('investment_experience')}  |  Financial Literacy: {prof.get('financial_literacy')}

=== BANK ACCOUNTS ===
{fmt_section('Accounts', sections.get('accounts', []), ['product_type', 'balance'])}
=== LOANS ===
{fmt_section('Loans', sections.get('loans', []), ['loan_type', 'lender_name', 'outstanding', 'emi', 'remaining_months', 'status'])}
=== CREDIT CARDS ===
{fmt_section('Credit Cards', sections.get('credit_cards', []), ['card_name', 'issuer', 'credit_limit', 'outstanding', 'utilisation_pct', 'status'])}
=== INVESTMENTS ===
{fmt_section('Investments', sections.get('investments', []), ['asset_type', 'asset_name', 'invested', 'current_value', 'gain_pct', 'monthly_sip', 'risk_level', 'status'])}
=== FIXED DEPOSITS ===
{fmt_section('FDs', sections.get('fixed_deposits', []), ['bank_name', 'principal', 'interest_rate', 'maturity_amount', 'maturity_date', 'status'])}
=== INSURANCE ===
{fmt_section('Insurance', sections.get('insurance', []), ['policy_type', 'policy_name', 'insurer', 'sum_assured', 'annual_premium', 'end_date', 'status'])}
=== RECENT TRANSACTIONS (last 20) ===
{pd.DataFrame(sections.get('recent_transactions', [])).to_string(index=False) if sections.get('recent_transactions') else '  No transactions found.'}
"""
        else:
            conn = sqlite3.connect("bank_data.db")
            query = """
                SELECT
                    c.address, c.age, c.customer_id, c.dob, c.gender, c.name, c.phone, c.postcode,
                    a.product_type, a.balance,
                    t.description, t.amount, t.type, t.date
                FROM "customers" c
                JOIN "accounts" a ON c.customer_id = a.customer_id
                LEFT JOIN "transactions" t ON a.account_id = t.account_id
                WHERE c.customer_id = ?
                ORDER BY t.date DESC
                LIMIT 200;
            """
            result_df = pd.read_sql_query(query, conn, params=[verified_id])
            conn.close()

            if result_df.empty:
                return "ERROR: No record found for this Customer ID."
            result = result_df.to_string(index=False)

        tool_context.state[cache_key] = result
        return result

    except Exception as e:
        return f"Database Error: {str(e)}"
