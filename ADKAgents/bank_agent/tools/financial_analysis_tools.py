import os
import sqlite3
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv

from ..observability.tool_tracer import traced_tool

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
BQ_DATASET = os.getenv("BQ_DATASET", "")


@lru_cache(maxsize=1)
def _bq_client():
    from google.cloud import bigquery
    return bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)


def _run_query(sql: str, params: list = None) -> pd.DataFrame:
    """Run SQL against BigQuery if configured, otherwise SQLite."""
    if BQ_DATASET:
        from google.cloud import bigquery
        client = _bq_client()
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

    Uses merchant_categories to classify transactions into Food & Dining, Shopping,
    Transportation, Utilities, Healthcare, Housing, and Entertainment. Also shows
    essential vs non-essential breakdown.

    Args:
        customer_id: The verified customer ID (e.g. 'C1001').

    Returns:
        A plain-text summary of spending by category and income/savings metrics.
    """
    try:
        customer_id = customer_id.strip().upper()
        if BQ_DATASET:
            from google.cloud import bigquery
            sql = f"""
                WITH account_ids AS (
                    SELECT account_id FROM `{BQ_DATASET}.accounts`
                    WHERE customer_id = @customer_id
                ),
                categorized AS (
                    SELECT
                        t.amount,
                        COALESCE(mc.category, 'Other') AS category,
                        COALESCE(mc.is_essential, FALSE) AS is_essential
                    FROM `{BQ_DATASET}.transactions` t
                    LEFT JOIN `{BQ_DATASET}.merchant_categories` mc
                        ON REGEXP_CONTAINS(UPPER(t.description), UPPER(mc.merchant_pattern))
                    WHERE t.account_id IN (SELECT account_id FROM account_ids)
                      AND t.type = 'debit'
                ),
                by_category AS (
                    SELECT
                        category,
                        ANY_VALUE(is_essential) AS is_essential,
                        ROUND(SUM(ABS(amount)), 2) AS total_spent,
                        COUNT(*) AS tx_count
                    FROM categorized
                    GROUP BY category
                ),
                income AS (
                    SELECT SUM(amount) AS total_income
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM account_ids)
                      AND type = 'credit'
                )
                SELECT
                    bc.category,
                    IF(bc.is_essential, 'Essential', 'Discretionary') AS spending_type,
                    bc.total_spent,
                    bc.tx_count AS transactions,
                    ROUND(bc.total_spent / 6, 2) AS avg_monthly,
                    ROUND(bc.total_spent / NULLIF(i.total_income, 0) * 100, 1) AS pct_of_income
                FROM by_category bc CROSS JOIN income i
                ORDER BY bc.total_spent DESC
            """
            params = [bigquery.ScalarQueryParameter("customer_id", "STRING", customer_id)]
            df = _run_query(sql, params)
            if df.empty:
                return f"No transaction data found for customer {customer_id}."

            essential = df[df["spending_type"] == "Essential"]["total_spent"].sum()
            discretionary = df[df["spending_type"] == "Discretionary"]["total_spent"].sum()
            total = essential + discretionary
            header = (
                f"Spending breakdown (6 months):\n"
                f"  Essential:     £{essential:>10,.0f}  ({essential/total*100:.0f}% of spend)\n"
                f"  Discretionary: £{discretionary:>10,.0f}  ({discretionary/total*100:.0f}% of spend)\n\n"
            )
            return header + df.to_string(index=False)
        else:
            sql = """
                SELECT t.category,
                    ROUND(SUM(CASE WHEN t.type='debit' THEN ABS(t.amount) ELSE 0 END),2) AS total_spent,
                    COUNT(CASE WHEN t.type='debit' THEN 1 END) AS transactions,
                    ROUND(SUM(CASE WHEN t.type='debit' THEN ABS(t.amount) ELSE 0 END)/6,2) AS avg_monthly
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                WHERE a.customer_id = ?
                  AND t.category NOT IN ('transfer','interest')
                GROUP BY t.category
                ORDER BY total_spent DESC
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
    """Full financial picture: cash flow, net worth, debt obligations, and savings opportunities.

    Covers bank accounts, fixed deposits, investments (mutual funds/ETFs), loans, and
    credit cards to show the complete savings and debt landscape.

    Args:
        customer_id: The verified customer ID.

    Returns:
        Plain-text summary of income, expenditure, net worth, and savings opportunities.
    """
    try:
        customer_id = customer_id.strip().upper()
        if BQ_DATASET:
            from google.cloud import bigquery
            sql = f"""
                WITH accts AS (
                    SELECT account_id, product_type, balance
                    FROM `{BQ_DATASET}.accounts` WHERE customer_id = @cid
                ),
                cash_flow AS (
                    SELECT
                        ROUND(SUM(CASE WHEN type='credit' THEN amount ELSE 0 END)/6, 2) AS avg_monthly_income,
                        ROUND(SUM(CASE WHEN type='debit' THEN ABS(amount) ELSE 0 END)/6, 2) AS avg_monthly_spend
                    FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM accts)
                ),
                inv AS (
                    SELECT
                        COALESCE(SUM(invested_amount), 0) AS total_invested,
                        COALESCE(SUM(current_value), 0) AS total_investment_value,
                        COALESCE(SUM(monthly_sip), 0) AS total_monthly_sip
                    FROM `{BQ_DATASET}.investments`
                    WHERE customer_id = @cid AND status = 'active'
                ),
                fd AS (
                    SELECT
                        COALESCE(SUM(principal_amount), 0) AS total_fd,
                        COALESCE(SUM(maturity_amount), 0) AS total_fd_maturity
                    FROM `{BQ_DATASET}.fixed_deposits`
                    WHERE customer_id = @cid AND LOWER(status) = 'active'
                ),
                loans AS (
                    SELECT
                        COALESCE(SUM(emi), 0) AS total_monthly_emi,
                        COALESCE(SUM(outstanding_amount), 0) AS total_loan_outstanding,
                        COUNT(*) AS active_loans
                    FROM `{BQ_DATASET}.loans`
                    WHERE customer_id = @cid AND status = 'active'
                ),
                cc AS (
                    SELECT
                        COALESCE(SUM(minimum_due), 0) AS total_min_cc_due,
                        COALESCE(SUM(current_outstanding), 0) AS total_cc_outstanding
                    FROM `{BQ_DATASET}.credit_cards`
                    WHERE customer_id = @cid AND status = 'active'
                )
                SELECT
                    cf.avg_monthly_income, cf.avg_monthly_spend,
                    (SELECT ROUND(SUM(balance), 2) FROM accts) AS total_bank_balance,
                    i.total_invested, i.total_investment_value, i.total_monthly_sip,
                    f.total_fd, f.total_fd_maturity,
                    l.total_monthly_emi, l.total_loan_outstanding, l.active_loans,
                    c.total_min_cc_due, c.total_cc_outstanding
                FROM cash_flow cf, inv i, fd f, loans l, cc c
            """
            params = [bigquery.ScalarQueryParameter("cid", "STRING", customer_id)]
            df = _run_query(sql, params)
            if df.empty:
                return f"No financial data found for customer {customer_id}."

            r = df.iloc[0]
            income = float(r["avg_monthly_income"] or 0)
            spend = float(r["avg_monthly_spend"] or 0)
            bank_balance = float(r["total_bank_balance"] or 0)
            total_invested = float(r["total_invested"] or 0)
            investment_value = float(r["total_investment_value"] or 0)
            monthly_sip = float(r["total_monthly_sip"] or 0)
            total_fd = float(r["total_fd"] or 0)
            fd_maturity = float(r["total_fd_maturity"] or 0)
            monthly_emi = float(r["total_monthly_emi"] or 0)
            loan_outstanding = float(r["total_loan_outstanding"] or 0)
            active_loans = int(r["active_loans"] or 0)
            min_cc_due = float(r["total_min_cc_due"] or 0)
            cc_outstanding = float(r["total_cc_outstanding"] or 0)

            total_obligations = monthly_emi + min_cc_due + monthly_sip
            free_cash_flow = round(income - spend - total_obligations, 2)
            savings_rate = round(free_cash_flow / income * 100, 1) if income else 0

            total_savings = bank_balance + total_fd + investment_value
            total_debt = loan_outstanding + cc_outstanding
            net_worth = round(total_savings - total_debt, 2)
            investment_gain = round(investment_value - total_invested, 2)

            return f"""=== SAVINGS & FINANCIAL OPPORTUNITY ===

CASH FLOW (monthly avg over 6 months):
  Income (credits):    £{income:>12,.0f}
  Expenses (debits):   £{spend:>12,.0f}
  Loan EMIs:           £{monthly_emi:>12,.0f}
  Credit card min due: £{min_cc_due:>12,.0f}
  Monthly SIP:         £{monthly_sip:>12,.0f}
  ─────────────────────────────────────
  Free cash flow:      £{free_cash_flow:>12,.0f}  ({savings_rate}% savings rate)

WEALTH SNAPSHOT:
  Bank accounts:       £{bank_balance:>12,.0f}
  Investments:         £{investment_value:>12,.0f}  (gain: £{investment_gain:+,.0f} on £{total_invested:,.0f} invested)
  Fixed deposits:      £{total_fd:>12,.0f}  (matures to £{fd_maturity:,.0f})
  ─────────────────────────────────────
  Total savings:       £{total_savings:>12,.0f}

DEBT POSITION:
  Active loans ({active_loans}):   £{loan_outstanding:>12,.0f} outstanding
  Credit cards:        £{cc_outstanding:>12,.0f} outstanding
  ─────────────────────────────────────
  Total debt:          £{total_debt:>12,.0f}
  Net worth:           £{net_worth:>12,.0f}
"""
        else:
            conn = sqlite3.connect("bank_data.db")
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
            spend = float(spend_df.iloc[0]["avg_monthly_spend"] or 0)
            surplus = round(income - spend, 2)
            rate = round(surplus / income * 100, 1) if income else 0
            overview = " | ".join(
                f"{r.product_type}: £{r.balance:.0f} @ {r.interest_rate}%"
                for _, r in accts_df.iterrows()
            )
            return (
                f"avg_monthly_income: {income}  avg_monthly_spend: {spend}  "
                f"monthly_surplus: {surplus}  savings_rate: {rate}%\n"
                f"Accounts: {overview}"
            )
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

        # Products table lives only in bank_data.db (not in BQ BANK_DATA dataset)
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
        customer_id = customer_id.strip().upper()
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
                WITH
                profile AS (
                    SELECT COALESCE(monthly_income, 0) AS monthly_income,
                           COALESCE(employment_type, 'unknown') AS employment_type,
                           COALESCE(risk_appetite, 'moderate') AS risk_appetite,
                           COALESCE(dependents, 0) AS dependents
                    FROM `{BQ_DATASET}.customer_profile`
                    WHERE customer_id = @cid
                ),
                accts AS (
                    SELECT account_id, product_type, balance
                    FROM `{BQ_DATASET}.accounts` WHERE customer_id = @cid
                ),
                txn AS (
                    SELECT amount, type FROM `{BQ_DATASET}.transactions`
                    WHERE account_id IN (SELECT account_id FROM accts)
                ),
                loans AS (
                    SELECT
                        COALESCE(SUM(emi), 0) AS total_emi,
                        COALESCE(SUM(outstanding_amount), 0) AS total_loan_outstanding,
                        COUNT(*) AS loan_count
                    FROM `{BQ_DATASET}.loans`
                    WHERE customer_id = @cid AND status = 'active'
                ),
                cc AS (
                    SELECT
                        COALESCE(SUM(minimum_due), 0) AS total_min_due,
                        COALESCE(SUM(current_outstanding), 0) AS total_cc_outstanding,
                        COALESCE(SUM(credit_limit), 0) AS total_credit_limit
                    FROM `{BQ_DATASET}.credit_cards`
                    WHERE customer_id = @cid AND status = 'active'
                ),
                inv AS (
                    SELECT
                        COALESCE(SUM(invested_amount), 0) AS total_invested,
                        COALESCE(SUM(current_value), 0) AS total_inv_value,
                        COALESCE(SUM(monthly_sip), 0) AS total_sip
                    FROM `{BQ_DATASET}.investments`
                    WHERE customer_id = @cid AND status = 'active'
                ),
                fd AS (
                    SELECT COALESCE(SUM(principal_amount), 0) AS total_fd
                    FROM `{BQ_DATASET}.fixed_deposits`
                    WHERE customer_id = @cid AND LOWER(status) = 'active'
                ),
                ins AS (
                    SELECT
                        COUNTIF(LOWER(policy_type) IN ('term_life','life','ulip')) > 0 AS has_life,
                        COUNTIF(LOWER(policy_type) IN ('health','medical')) > 0 AS has_health
                    FROM `{BQ_DATASET}.insurance`
                    WHERE customer_id = @cid AND LOWER(status) = 'active'
                )
                SELECT
                    p.monthly_income, p.employment_type, p.risk_appetite, p.dependents,
                    ROUND(SUM(CASE WHEN t.type='credit' THEN t.amount ELSE 0 END)/6, 2) AS avg_monthly_income_txn,
                    ROUND(SUM(CASE WHEN t.type='debit' THEN ABS(t.amount) ELSE 0 END)/6, 2) AS avg_monthly_spend,
                    (SELECT ROUND(SUM(balance), 2) FROM accts) AS total_bank_balance,
                    l.total_emi, l.total_loan_outstanding, l.loan_count,
                    c.total_min_due, c.total_cc_outstanding, c.total_credit_limit,
                    i.total_invested, i.total_inv_value, i.total_sip,
                    f.total_fd,
                    ins.has_life, ins.has_health
                FROM txn t, profile p, loans l, cc c, inv i, fd f, ins
                GROUP BY p.monthly_income, p.employment_type, p.risk_appetite, p.dependents,
                         l.total_emi, l.total_loan_outstanding, l.loan_count,
                         c.total_min_due, c.total_cc_outstanding, c.total_credit_limit,
                         i.total_invested, i.total_inv_value, i.total_sip,
                         f.total_fd, ins.has_life, ins.has_health
            """
            params = [bigquery.ScalarQueryParameter("cid", "STRING", customer_id)]
            row = _run_query(sql, params).iloc[0]

            profile_income   = float(row["monthly_income"] or 0)
            txn_income       = float(row["avg_monthly_income_txn"] or 0)
            avg_monthly_income = profile_income if profile_income > 0 else txn_income
            avg_monthly_spend  = float(row["avg_monthly_spend"] or 0)
            total_bank_balance = float(row["total_bank_balance"] or 0)
            total_emi          = float(row["total_emi"] or 0)
            loan_outstanding   = float(row["total_loan_outstanding"] or 0)
            loan_count         = int(row["loan_count"] or 0)
            total_min_due      = float(row["total_min_due"] or 0)
            cc_outstanding     = float(row["total_cc_outstanding"] or 0)
            credit_limit       = float(row["total_credit_limit"] or 0)
            total_invested     = float(row["total_invested"] or 0)
            inv_value          = float(row["total_inv_value"] or 0)
            total_sip          = float(row["total_sip"] or 0)
            total_fd           = float(row["total_fd"] or 0)
            has_life           = bool(row["has_life"])
            has_health         = bool(row["has_health"])
            risk_appetite      = str(row["risk_appetite"] or "moderate")
            employment_type    = str(row["employment_type"] or "")

            monthly_obligations = total_emi + total_min_due + total_sip
            free_cash_flow = avg_monthly_income - avg_monthly_spend - monthly_obligations
            savings_rate = round(free_cash_flow / avg_monthly_income * 100, 1) if avg_monthly_income else 0
            months_cushion = round(total_bank_balance / avg_monthly_spend, 1) if avg_monthly_spend else 0

            # ── 1. Cash Flow & Savings (25 pts) ──────────────────────────────
            cash_flow_score = min(25, max(0, savings_rate / 20 * 25))

            # ── 2. Debt Health (25 pts) ───────────────────────────────────────
            dti = (total_emi + total_min_due) / avg_monthly_income * 100 if avg_monthly_income else 100
            dti_score = (25 if dti < 20 else 18 if dti < 30 else 12 if dti < 40 else 5 if dti < 50 else 0)
            cc_util = cc_outstanding / credit_limit * 100 if credit_limit else 0
            cc_penalty = max(0, (cc_util - 30) / 70 * 5) if cc_util > 30 else 0
            debt_score = max(0, round(dti_score - cc_penalty, 1))

            # ── 3. Liquid Safety Net (20 pts) ─────────────────────────────────
            cushion_score = min(20, max(0, round(months_cushion / 6 * 20, 1)))

            # ── 4. Savings & Investments (20 pts) ────────────────────────────
            total_wealth = inv_value + total_fd
            wealth_to_income = total_wealth / (avg_monthly_income * 12) if avg_monthly_income else 0
            investment_score = min(20, max(0, round(wealth_to_income / 2 * 20, 1)))

            # ── 5. Insurance Protection (10 pts) ─────────────────────────────
            insurance_score = (5 if has_life else 0) + (5 if has_health else 0)

            total_score = round(cash_flow_score + debt_score + cushion_score + investment_score + insurance_score, 1)
            rating = (
                "Excellent"       if total_score >= 80 else
                "Good"            if total_score >= 60 else
                "Fair"            if total_score >= 40 else
                "Needs Attention"
            )
            investment_gain = round(inv_value - total_invested, 2)

            return f"""FINANCIAL WELLBEING SCORE: {total_score}/100 — {rating}

Dimension Breakdown:
  Cash Flow & Savings: {cash_flow_score:.1f}/25  (£{free_cash_flow:,.0f}/month free, {savings_rate}% savings rate)
  Debt Health:         {debt_score:.1f}/25  (DTI {dti:.0f}%, {loan_count} loan(s), CC utilisation {cc_util:.0f}%)
  Liquid Safety Net:   {cushion_score:.1f}/20  ({months_cushion:.1f} months of expenses in bank)
  Savings & Invest.:   {investment_score:.1f}/20  (£{total_wealth:,.0f} in FDs + investments, {wealth_to_income:.1f}× annual income)
  Insurance:           {insurance_score:.1f}/10  ({'Life ✓' if has_life else 'Life ✗'}  {'Health ✓' if has_health else 'Health ✗'})

Key Metrics:
  Monthly Income:      £{avg_monthly_income:>12,.0f}  [{employment_type}]
  Monthly Expenses:    £{avg_monthly_spend:>12,.0f}
  Loan EMIs + CC due:  £{monthly_obligations:>12,.0f}
  Free Cash Flow:      £{free_cash_flow:>12,.0f}
  Bank Balance:        £{total_bank_balance:>12,.0f}
  Investments:         £{inv_value:>12,.0f}  (gain: £{investment_gain:+,.0f})
  Fixed Deposits:      £{total_fd:>12,.0f}
  Loans Outstanding:   £{loan_outstanding:>12,.0f}
  CC Outstanding:      £{cc_outstanding:>12,.0f}
  Risk Appetite:       {risk_appetite}
"""

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
