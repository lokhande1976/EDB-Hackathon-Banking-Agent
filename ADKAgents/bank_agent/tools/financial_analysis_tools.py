import os
import sqlite3

import pandas as pd
from dotenv import load_dotenv

from ..observability.tool_tracer import traced_tool

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
BQ_DATASET = os.getenv("BQ_DATASET", "")


def _run_query(sql: str, params: list = None) -> pd.DataFrame:
    """Run SQL against BigQuery if configured, otherwise SQLite."""
    if BQ_DATASET:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)
        job_config = None
        if params:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
        return client.query(sql, job_config=job_config).to_dataframe()
    else:
        conn = sqlite3.connect("bank_data.db")
        # Replace BQ-style named params (@name) with SQLite positional (?)
        import re
        values = []
        if params:
            for p in params:
                sql = re.sub(rf"@{p.name}", "?", sql, count=1)
                values.append(p.value)
        df = pd.read_sql_query(sql, conn, params=values if values else None)
        conn.close()
        return df


@traced_tool
def get_spending_analysis(customer_id: str) -> str:
    """Analyse a customer's spending patterns by category over the last 6 months.

    Args:
        customer_id: The verified customer ID (e.g. 'C001').

    Returns:
        A plain-text summary of spending by category and income/savings metrics.
    """
    try:
        if BQ_DATASET:
            from google.cloud import bigquery
            sql = f"""
                WITH account_ids AS (
                    SELECT account_id FROM `{BQ_DATASET}.accounts`
                    WHERE customer_id = @customer_id
                ),
                spend AS (
                    SELECT category,
                        SUM(CASE WHEN type='debit' THEN ABS(amount) ELSE 0 END) AS total_spent,
                        COUNT(CASE WHEN type='debit' THEN 1 END) AS tx_count
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM account_ids)
                      AND category NOT IN ('transfer','interest')
                    GROUP BY category
                ),
                income AS (
                    SELECT SUM(amount) AS total_income
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM account_ids)
                      AND category = 'income'
                )
                SELECT s.category,
                    ROUND(s.total_spent,2) AS total_spent_gbp,
                    s.tx_count AS transaction_count,
                    ROUND(s.total_spent/6,2) AS avg_monthly_gbp,
                    ROUND(s.total_spent/NULLIF(i.total_income,0)*100,1) AS pct_of_income
                FROM spend s CROSS JOIN income i
                ORDER BY s.total_spent DESC
            """
            params = [bigquery.ScalarQueryParameter("customer_id", "STRING", customer_id)]
            df = _run_query(sql, params)
        else:
            sql = """
                SELECT t.category,
                    ROUND(SUM(CASE WHEN t.type='debit' THEN ABS(t.amount) ELSE 0 END),2) AS total_spent_gbp,
                    COUNT(CASE WHEN t.type='debit' THEN 1 END) AS transaction_count,
                    ROUND(SUM(CASE WHEN t.type='debit' THEN ABS(t.amount) ELSE 0 END)/6,2) AS avg_monthly_gbp
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                WHERE a.customer_id = ?
                  AND t.category NOT IN ('transfer','interest')
                GROUP BY t.category
                ORDER BY total_spent_gbp DESC
            """
            conn = sqlite3.connect("bank_data.db")
            df = pd.read_sql_query(sql, conn, params=[customer_id])
            conn.close()

        if df.empty:
            return f"No transaction data found for customer {customer_id}."
        return df.to_string(index=False)
    except Exception as e:
        return f"Error running spending analysis: {str(e)}"


@traced_tool
def get_savings_opportunity(customer_id: str) -> str:
    """Identify monthly surplus, savings rate, and idle cash opportunity.

    Args:
        customer_id: The verified customer ID.

    Returns:
        Plain-text summary of income, expenditure, and savings opportunities.
    """
    try:
        conn = sqlite3.connect("bank_data.db") if not BQ_DATASET else None

        if BQ_DATASET:
            from google.cloud import bigquery
            sql = f"""
                WITH accts AS (SELECT account_id, product_type, balance, interest_rate
                               FROM `{BQ_DATASET}.accounts` WHERE customer_id = @customer_id),
                income AS (
                    SELECT ROUND(SUM(amount)/6,2) AS avg_monthly_income
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM accts) AND category='income'
                ),
                spend AS (
                    SELECT ROUND(SUM(ABS(amount))/6,2) AS avg_monthly_spend
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM accts)
                      AND type='debit' AND category NOT IN ('transfer','interest')
                )
                SELECT i.avg_monthly_income, s.avg_monthly_spend,
                    ROUND(i.avg_monthly_income - s.avg_monthly_spend,2) AS monthly_surplus,
                    ROUND((i.avg_monthly_income - s.avg_monthly_spend)/NULLIF(i.avg_monthly_income,0)*100,1) AS savings_rate_pct,
                    (SELECT STRING_AGG(CONCAT(product_type,': £',CAST(ROUND(balance,0) AS STRING),' @ ',CAST(interest_rate AS STRING),'%'),' | ')
                     FROM accts) AS accounts_overview
                FROM income i CROSS JOIN spend s
            """
            params = [bigquery.ScalarQueryParameter("customer_id", "STRING", customer_id)]
            df = _run_query(sql, params)
        else:
            income_df = pd.read_sql_query(
                "SELECT ROUND(SUM(amount)/6,2) AS avg_monthly_income FROM transactions t "
                "JOIN accounts a ON t.account_id=a.account_id "
                "WHERE a.customer_id=? AND t.category='income'",
                conn, params=[customer_id]
            )
            spend_df = pd.read_sql_query(
                "SELECT ROUND(SUM(ABS(amount))/6,2) AS avg_monthly_spend FROM transactions t "
                "JOIN accounts a ON t.account_id=a.account_id "
                "WHERE a.customer_id=? AND t.type='debit' AND t.category NOT IN ('transfer','interest')",
                conn, params=[customer_id]
            )
            accts_df = pd.read_sql_query(
                "SELECT product_type, balance, interest_rate FROM accounts WHERE customer_id=?",
                conn, params=[customer_id]
            )
            conn.close()

            income = float(income_df.iloc[0]["avg_monthly_income"] or 0)
            spend  = float(spend_df.iloc[0]["avg_monthly_spend"] or 0)
            surplus = round(income - spend, 2)
            rate = round(surplus / income * 100, 1) if income else 0
            overview = " | ".join(
                f"{r.product_type}: £{r.balance:.0f} @ {r.interest_rate}%"
                for _, r in accts_df.iterrows()
            )
            result = (
                f"avg_monthly_income    avg_monthly_spend    monthly_surplus    savings_rate_pct    accounts_overview\n"
                f"{income:>20}    {spend:>17}    {surplus:>14}    {rate:>16}    {overview}"
            )
            return result

        if df.empty:
            return f"No financial data found for customer {customer_id}."
        return df.to_string(index=False)
    except Exception as e:
        return f"Error calculating savings opportunity: {str(e)}"


@traced_tool
def get_product_recommendations(
    access_type: str = "any",
    max_monthly_fee: float = 0.0,
    min_interest_rate: float = 0.0,
    product_type: str = "savings",
) -> str:
    """Query the product catalogue and return matching banking products.

    Args:
        access_type: 'instant', 'notice', 'fixed', or 'any'.
        max_monthly_fee: Maximum monthly fee in GBP (0 = no fee).
        min_interest_rate: Minimum AER interest rate.
        product_type: 'savings', 'isa', 'current', or 'any'.

    Returns:
        A table of matching products with key features.
    """
    try:
        conditions = ["is_active = 1"]
        params = []

        if access_type != "any":
            conditions.append("access_type = ?")
            params.append(access_type)
        if max_monthly_fee == 0.0:
            conditions.append("monthly_fee = 0")
        else:
            conditions.append("monthly_fee <= ?")
            params.append(max_monthly_fee)
        if min_interest_rate > 0:
            conditions.append("interest_rate_pa >= ?")
            params.append(min_interest_rate)
        if product_type != "any":
            conditions.append("product_type = ?")
            params.append(product_type)

        where = " AND ".join(conditions)

        if BQ_DATASET:
            from google.cloud import bigquery
            bq_params = []
            bq_where = ["is_active = TRUE"]
            if access_type != "any":
                bq_where.append("access_type = @access_type")
                bq_params.append(bigquery.ScalarQueryParameter("access_type", "STRING", access_type))
            if max_monthly_fee == 0.0:
                bq_where.append("monthly_fee = 0")
            else:
                bq_where.append("monthly_fee <= @max_fee")
                bq_params.append(bigquery.ScalarQueryParameter("max_fee", "FLOAT64", max_monthly_fee))
            if min_interest_rate > 0:
                bq_where.append("interest_rate_pa >= @min_rate")
                bq_params.append(bigquery.ScalarQueryParameter("min_rate", "FLOAT64", min_interest_rate))
            if product_type != "any":
                bq_where.append("product_type = @product_type")
                bq_params.append(bigquery.ScalarQueryParameter("product_type", "STRING", product_type))

            sql = f"""
                SELECT product_name, product_type, interest_rate_pa AS aer_pct,
                    monthly_fee AS monthly_fee_gbp, min_deposit AS min_deposit_gbp,
                    access_type, features, target_segment
                FROM `{BQ_DATASET}.products`
                WHERE {" AND ".join(bq_where)}
                ORDER BY interest_rate_pa DESC
            """
            df = _run_query(sql, bq_params)
        else:
            sql = f"""
                SELECT product_name, product_type, interest_rate_pa AS aer_pct,
                    monthly_fee AS monthly_fee_gbp, min_deposit AS min_deposit_gbp,
                    access_type, features, target_segment
                FROM products
                WHERE {where}
                ORDER BY interest_rate_pa DESC
            """
            conn = sqlite3.connect("bank_data.db")
            df = pd.read_sql_query(sql, conn, params=params if params else None)
            conn.close()

        if df.empty:
            return "No products found matching those criteria."
        return df.to_string(index=False)
    except Exception as e:
        return f"Error fetching product recommendations: {str(e)}"


@traced_tool
def calculate_financial_wellbeing_score(customer_id: str) -> str:
    """Calculate a holistic financial wellbeing score (0-100) for a customer.

    Args:
        customer_id: The verified customer ID.

    Returns:
        Wellbeing report with score, dimension breakdown, and action recommendations.
    """
    try:
        conn = sqlite3.connect("bank_data.db") if not BQ_DATASET else None

        if not BQ_DATASET:
            accts = pd.read_sql_query(
                "SELECT account_id, account_type, balance, interest_rate FROM accounts WHERE customer_id=?",
                conn, params=[customer_id]
            )
            ids = tuple(accts["account_id"].tolist())
            if not ids:
                return f"No accounts found for {customer_id}."

            placeholders = ",".join(["?" for _ in ids])
            txns = pd.read_sql_query(
                f"SELECT amount, type, category FROM transactions WHERE account_id IN ({placeholders})",
                conn, params=list(ids)
            )
            conn.close()

            income = txns[txns["category"] == "income"]["amount"].sum()
            avg_monthly_income = round(income / 6, 2)

            spend = txns[(txns["type"] == "debit") & (~txns["category"].isin(["transfer","interest"]))]["amount"].abs().sum()
            avg_monthly_spend = round(spend / 6, 2)

            months_with_income = min(6, len(txns[txns["category"] == "income"]))
            monthly_surplus = round(avg_monthly_income - avg_monthly_spend, 2)
            savings_rate = round(monthly_surplus / avg_monthly_income * 100, 1) if avg_monthly_income else 0

            current_balance = accts[accts["account_type"] == "current"]["balance"].sum()
            months_cushion = round(current_balance / avg_monthly_spend, 2) if avg_monthly_spend else 0
            liability_count = len(accts[accts["balance"] < 0])
            total_accounts = len(accts)
        else:
            from google.cloud import bigquery
            sql = f"""
                WITH accts AS (SELECT account_id, account_type, balance, interest_rate
                               FROM `{BQ_DATASET}.accounts` WHERE customer_id=@cid),
                txn AS (SELECT amount,type,category FROM `{BQ_DATASET}.transactions`
                        WHERE account_id IN (SELECT account_id FROM accts))
                SELECT
                    COUNT(DISTINCT CASE WHEN category='income' THEN 1 END) AS months_with_income,
                    ROUND(SUM(CASE WHEN category='income' THEN amount ELSE 0 END)/6,2) AS avg_monthly_income,
                    ROUND(SUM(CASE WHEN type='debit' AND category NOT IN ('transfer','interest') THEN ABS(amount) ELSE 0 END)/6,2) AS avg_monthly_spend,
                    (SELECT ROUND(SUM(balance),2) FROM accts WHERE account_type='current') AS current_balance,
                    (SELECT COUNT(*) FROM accts WHERE balance<0) AS liability_count,
                    (SELECT COUNT(*) FROM accts) AS total_accounts
                FROM txn
            """
            params = [bigquery.ScalarQueryParameter("cid", "STRING", customer_id)]
            row = _run_query(sql, params).iloc[0]
            avg_monthly_income = float(row["avg_monthly_income"] or 0)
            avg_monthly_spend  = float(row["avg_monthly_spend"] or 0)
            months_with_income = int(row["months_with_income"] or 0)
            monthly_surplus    = round(avg_monthly_income - avg_monthly_spend, 2)
            savings_rate       = round(monthly_surplus / avg_monthly_income * 100, 1) if avg_monthly_income else 0
            current_balance    = float(row["current_balance"] or 0)
            months_cushion     = round(current_balance / avg_monthly_spend, 2) if avg_monthly_spend else 0
            liability_count    = int(row["liability_count"] or 0)
            total_accounts     = int(row["total_accounts"] or 1)

        income_score  = min(25, months_with_income / 6 * 25)
        savings_score = min(25, max(0, savings_rate / 20 * 25))
        cushion_score = min(25, max(0, months_cushion / 3 * 25))
        liability_pct = liability_count / max(1, total_accounts)
        debt_score    = max(0, 25 * (1 - liability_pct))
        total_score   = round(income_score + savings_score + cushion_score + debt_score, 1)

        rating = (
            "Excellent"       if total_score >= 80 else
            "Good"            if total_score >= 60 else
            "Fair"            if total_score >= 40 else
            "Needs Attention"
        )

        return f"""FINANCIAL WELLBEING SCORE: {total_score}/100 — {rating}

Dimension Breakdown:
  Income Stability:  {round(income_score,1)}/25  (income received in {months_with_income}/6 months)
  Savings Rate:      {round(savings_score,1)}/25  ({savings_rate}% of income saved monthly)
  Financial Cushion: {round(cushion_score,1)}/25  ({months_cushion:.1f} months of spend in current account)
  Debt Burden:       {round(debt_score,1)}/25  ({liability_count} liability account(s))

Key Metrics:
  Average Monthly Income:  £{avg_monthly_income:,.2f}
  Average Monthly Spend:   £{avg_monthly_spend:,.2f}
  Monthly Surplus:         £{monthly_surplus:,.2f}
  Current Account Balance: £{current_balance:,.2f}
"""
    except Exception as e:
        return f"Error calculating wellbeing score: {str(e)}"
