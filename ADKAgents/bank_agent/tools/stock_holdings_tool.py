import sqlite3

import pandas as pd

from ..observability.tool_tracer import traced_tool

# Current market prices (pence) — representative snapshot used for P&L calculation
CURRENT_PRICES = {
    "LLOY": 56.20,
    "HSBA": 652.0,
    "BARC": 218.0,
    "BP":   482.0,
    "SHEL": 2740.0,
    "VOD":  72.0,
    "AZN":  12800.0,
    "GSK":  1750.0,
    "TSCO": 358.0,
    "NWG":  345.0,
}


def _conn() -> sqlite3.Connection:
    return sqlite3.connect("bank_data.db")


@traced_tool
def get_customer_holdings(customer_id: str) -> str:
    """Return a customer's stock portfolio with current value and P&L.

    Args:
        customer_id: The verified customer ID (e.g. 'C001').

    Returns:
        Table of holdings with shares, avg buy price, current price,
        current value (£), and unrealised gain/loss (£ and %).
    """
    try:
        conn = _conn()
        df = pd.read_sql_query(
            "SELECT ticker, company_name, sector, shares, avg_buy_price "
            "FROM stock_holdings WHERE customer_id = ? ORDER BY ticker",
            conn, params=[customer_id]
        )
        conn.close()

        if df.empty:
            return f"No stock holdings found for customer {customer_id}."

        rows = []
        for _, r in df.iterrows():
            cur = CURRENT_PRICES.get(r["ticker"], r["avg_buy_price"])
            cost  = r["shares"] * r["avg_buy_price"] / 100
            value = r["shares"] * cur / 100
            gain  = value - cost
            pct   = gain / cost * 100 if cost else 0
            rows.append({
                "ticker":       r["ticker"],
                "company":      r["company_name"],
                "sector":       r["sector"],
                "shares":       int(r["shares"]),
                "avg_buy_p":    f"{r['avg_buy_price']:.1f}p",
                "current_p":    f"{cur:.1f}p",
                "value_gbp":    f"£{value:,.2f}",
                "gain_loss_gbp": f"{'+' if gain >= 0 else ''}£{gain:,.2f}",
                "gain_loss_pct": f"{pct:+.1f}%",
            })

        out_df = pd.DataFrame(rows)
        total_value = sum(r["shares"] * CURRENT_PRICES.get(r["ticker"], r["avg_buy_price"]) / 100
                         for _, r in df.iterrows())
        total_cost  = sum(r["shares"] * r["avg_buy_price"] / 100 for _, r in df.iterrows())
        total_gain  = total_value - total_cost

        return (
            f"Stock portfolio for {customer_id}:\n"
            f"{out_df.to_string(index=False)}\n\n"
            f"Portfolio total value : £{total_value:,.2f}\n"
            f"Total unrealised P&L  : {'+' if total_gain >= 0 else ''}£{total_gain:,.2f}"
        )
    except Exception as e:
        return f"Error fetching holdings: {e}"


@traced_tool
def get_portfolio_wellbeing(customer_id: str) -> str:
    """Assess the investment dimension of a customer's financial wellbeing.

    Returns portfolio value, diversification score, and investment-adjusted
    net worth to feed into the financial wellbeing score.

    Args:
        customer_id: The verified customer ID.
    """
    try:
        conn = _conn()
        df = pd.read_sql_query(
            "SELECT ticker, sector, shares, avg_buy_price FROM stock_holdings WHERE customer_id = ?",
            conn, params=[customer_id]
        )
        accounts = pd.read_sql_query(
            "SELECT SUM(balance) as total_savings FROM accounts WHERE customer_id = ? AND account_type != 'current'",
            conn, params=[customer_id]
        )
        conn.close()

        if df.empty:
            return f"No investment holdings for {customer_id}. Investment score: 0/25."

        total_value = sum(
            r["shares"] * CURRENT_PRICES.get(r["ticker"], r["avg_buy_price"]) / 100
            for _, r in df.iterrows()
        )
        total_cost = sum(r["shares"] * r["avg_buy_price"] / 100 for _, r in df.iterrows())
        total_gain = total_value - total_cost

        sectors = df["sector"].nunique()
        tickers = df["ticker"].nunique()
        # Diversification: 1 ticker = poor, 3+ tickers across 2+ sectors = good
        div_score = min(25, (tickers * 5) + (sectors * 3))

        savings = float(accounts.iloc[0]["total_savings"] or 0)
        net_worth = savings + total_value

        return (
            f"Investment Wellbeing for {customer_id}:\n"
            f"  Portfolio value       : £{total_value:,.2f}\n"
            f"  Unrealised P&L        : {'+' if total_gain >= 0 else ''}£{total_gain:,.2f}\n"
            f"  Holdings              : {tickers} stocks across {sectors} sector(s)\n"
            f"  Diversification score : {div_score}/25\n"
            f"  Total net worth (excl. property) : £{net_worth:,.2f}"
        )
    except Exception as e:
        return f"Error assessing portfolio wellbeing: {e}"
