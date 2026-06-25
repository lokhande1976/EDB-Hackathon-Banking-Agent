import sqlite3

import pandas as pd

from ..observability.tool_tracer import traced_tool


def _conn() -> sqlite3.Connection:
    return sqlite3.connect("bank_data.db")


@traced_tool
def get_stock_price(date: str) -> str:
    """Return Lloyds Banking Group (LLOY) OHLCV data for a specific trading date.

    Args:
        date: Trading date in YYYY-MM-DD format (e.g. '2019-03-15').

    Returns:
        Open, high, low, close prices (in pence) and trading volume for that day,
        or a message if the date is not a trading day.
    """
    try:
        conn = _conn()
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM lloyds_stock WHERE date = ?",
            conn, params=[date]
        )
        conn.close()
        if df.empty:
            return f"No trading data for {date}. It may be a weekend or public holiday."
        r = df.iloc[0]
        return (
            f"Lloyds Banking Group (LLOY) on {r['date']}:\n"
            f"  Open:   {r['open']:.2f}p\n"
            f"  High:   {r['high']:.2f}p\n"
            f"  Low:    {r['low']:.2f}p\n"
            f"  Close:  {r['close']:.2f}p\n"
            f"  Volume: {int(r['volume']):,} shares"
        )
    except Exception as e:
        return f"Error fetching stock price: {e}"


@traced_tool
def get_stock_price_range(start_date: str, end_date: str) -> str:
    """Return daily Lloyds (LLOY) closing prices for a date range.

    Args:
        start_date: Start of the range in YYYY-MM-DD format (inclusive).
        end_date: End of the range in YYYY-MM-DD format (inclusive).

    Returns:
        A table of dates and closing prices, plus range high/low/avg.
    """
    try:
        conn = _conn()
        df = pd.read_sql_query(
            "SELECT date, close, volume FROM lloyds_stock WHERE date BETWEEN ? AND ? ORDER BY date",
            conn, params=[start_date, end_date]
        )
        conn.close()
        if df.empty:
            return f"No trading data found between {start_date} and {end_date}."
        summary = (
            f"LLOY closing prices {start_date} to {end_date} ({len(df)} trading days):\n"
            f"  High:  {df['close'].max():.2f}p  |  Low: {df['close'].min():.2f}p  |  Avg: {df['close'].mean():.2f}p\n\n"
        )
        table = df.rename(columns={"close": "close_p", "volume": "volume_shares"}).to_string(index=False)
        return summary + table
    except Exception as e:
        return f"Error fetching price range: {e}"


@traced_tool
def get_stock_stats(period: str) -> str:
    """Return aggregate Lloyds (LLOY) stock statistics for a given period.

    Args:
        period: One of 'all', a 4-digit year (e.g. '2018'), or 'YYYY-MM' (e.g. '2018-06').

    Returns:
        High, low, average close, total volume, and price change for the period.
    """
    try:
        conn = _conn()

        if period == "all":
            sql = "SELECT * FROM lloyds_stock ORDER BY date"
            df = pd.read_sql_query(sql, conn)
            label = "All available history"
        elif len(period) == 4 and period.isdigit():
            df = pd.read_sql_query(
                "SELECT * FROM lloyds_stock WHERE strftime('%Y', date) = ? ORDER BY date",
                conn, params=[period]
            )
            label = f"Year {period}"
        elif len(period) == 7 and period[4] == "-":
            df = pd.read_sql_query(
                "SELECT * FROM lloyds_stock WHERE strftime('%Y-%m', date) = ? ORDER BY date",
                conn, params=[period]
            )
            label = period
        else:
            return "Invalid period. Use 'all', a 4-digit year like '2018', or 'YYYY-MM' like '2018-06'."

        conn.close()

        if df.empty:
            return f"No data found for period '{period}'."

        start_close = df.iloc[0]["close"]
        end_close   = df.iloc[-1]["close"]
        change      = end_close - start_close
        pct_change  = change / start_close * 100

        return (
            f"LLOY Stock Statistics — {label}:\n"
            f"  Trading days  : {len(df)}\n"
            f"  Date range    : {df.iloc[0]['date']} → {df.iloc[-1]['date']}\n"
            f"  Highest close : {df['close'].max():.2f}p\n"
            f"  Lowest close  : {df['close'].min():.2f}p\n"
            f"  Average close : {df['close'].mean():.2f}p\n"
            f"  Start close   : {start_close:.2f}p\n"
            f"  End close     : {end_close:.2f}p\n"
            f"  Price change  : {change:+.2f}p ({pct_change:+.1f}%)\n"
            f"  Total volume  : {int(df['volume'].sum()):,} shares"
        )
    except Exception as e:
        return f"Error fetching stock stats: {e}"
