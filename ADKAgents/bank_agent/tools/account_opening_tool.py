import os
import sqlite3
import uuid
from datetime import date

from dotenv import load_dotenv
from google.adk.tools.tool_context import ToolContext

from ..observability.tool_tracer import traced_tool

load_dotenv()

BQ_DATASET = os.getenv("BQ_DATASET", "")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS applications (
        application_id TEXT PRIMARY KEY,
        customer_id    TEXT NOT NULL,
        product_name   TEXT NOT NULL,
        product_type   TEXT,
        interest_rate  REAL,
        status         TEXT DEFAULT 'submitted',
        applied_date   TEXT,
        product_url    TEXT
    )
"""


def _ensure_applications_table(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()


@traced_tool
def open_account(product_name: str, tool_context: ToolContext) -> dict:
    """Opens a new bank account/product for the currently verified customer.

    Args:
        product_name: Exact product name to open (e.g. "Fixed Rate Saver 2 Year").
        tool_context: Session context — must have identity_verified = True.

    Returns:
        dict with status, application_id, and product details on success.
    """
    if not tool_context.state.get("identity_verified"):
        return {
            "status": "error",
            "error_message": (
                "Customer identity not verified. "
                "Please verify identity before opening an account."
            ),
        }

    customer_id = tool_context.state.get("verified_customer_id", "")
    if not customer_id:
        return {"status": "error", "error_message": "No verified customer ID in session."}

    try:
        if BQ_DATASET:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)

            query = f"""
                SELECT product_name, product_type, interest_rate_pa, product_url
                FROM `{BQ_DATASET}.products`
                WHERE LOWER(product_name) = LOWER(@pname)
                LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("pname", "STRING", product_name)]
            )
            df = client.query(query, job_config=job_config).to_dataframe()
            if df.empty:
                return {
                    "status": "error",
                    "error_message": f"Product '{product_name}' not found in Lloyds product catalogue.",
                }
            row = df.iloc[0]
            pname, ptype, rate, purl = (
                row["product_name"],
                row["product_type"],
                float(row["interest_rate_pa"] or 0),
                row.get("product_url", ""),
            )

            application_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
            applied_date = date.today().isoformat()

            insert = f"""
                INSERT INTO `{BQ_DATASET}.applications`
                    (application_id, customer_id, product_name, product_type,
                     interest_rate, status, applied_date, product_url)
                VALUES
                    (@aid, @cid, @pname, @ptype, @rate, 'submitted', @dt, @url)
            """
            job_config2 = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("aid", "STRING", application_id),
                    bigquery.ScalarQueryParameter("cid", "STRING", customer_id),
                    bigquery.ScalarQueryParameter("pname", "STRING", pname),
                    bigquery.ScalarQueryParameter("ptype", "STRING", ptype),
                    bigquery.ScalarQueryParameter("rate", "FLOAT64", rate),
                    bigquery.ScalarQueryParameter("dt", "STRING", applied_date),
                    bigquery.ScalarQueryParameter("url", "STRING", purl or ""),
                ]
            )
            client.query(insert, job_config=job_config2).result()

        else:
            conn = sqlite3.connect("bank_data.db")
            _ensure_applications_table(conn)

            cursor = conn.cursor()
            cursor.execute(
                "SELECT product_name, product_type, interest_rate_pa, product_url "
                "FROM products WHERE LOWER(product_name) = LOWER(?)",
                [product_name],
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {
                    "status": "error",
                    "error_message": f"Product '{product_name}' not found in Lloyds product catalogue.",
                }
            pname, ptype, rate, purl = row

            application_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
            applied_date = date.today().isoformat()

            cursor.execute(
                """INSERT INTO applications
                       (application_id, customer_id, product_name, product_type,
                        interest_rate, status, applied_date, product_url)
                   VALUES (?, ?, ?, ?, ?, 'submitted', ?, ?)""",
                [application_id, customer_id, pname, ptype, rate, applied_date, purl or ""],
            )
            conn.commit()
            conn.close()

        return {
            "status": "success",
            "application_id": application_id,
            "customer_id": customer_id,
            "product_name": pname,
            "product_type": ptype,
            "interest_rate_pa": rate,
            "applied_date": applied_date,
            "product_url": purl or "",
        }

    except Exception as exc:
        return {"status": "error", "error_message": f"Database error: {exc}"}


@traced_tool
def get_account_applications(tool_context: ToolContext) -> dict:
    """Retrieves all account applications for the currently verified customer.

    Args:
        tool_context: Session context — must have identity_verified = True.

    Returns:
        dict with status and list of applications.
    """
    if not tool_context.state.get("identity_verified"):
        return {"status": "error", "error_message": "Customer identity not verified."}

    customer_id = tool_context.state.get("verified_customer_id", "")

    try:
        if BQ_DATASET:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)
            query = f"""
                SELECT application_id, product_name, product_type,
                       status, applied_date, interest_rate
                FROM `{BQ_DATASET}.applications`
                WHERE customer_id = @cid
                ORDER BY applied_date DESC
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("cid", "STRING", customer_id)]
            )
            df = client.query(query, job_config=job_config).to_dataframe()
            apps = df.to_dict(orient="records")
        else:
            conn = sqlite3.connect("bank_data.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
            )
            if not cursor.fetchone():
                conn.close()
                return {"status": "success", "applications": []}

            cursor.execute(
                """SELECT application_id, product_name, product_type,
                          status, applied_date, interest_rate
                   FROM applications WHERE customer_id = ?
                   ORDER BY applied_date DESC""",
                [customer_id],
            )
            cols = ["application_id", "product_name", "product_type",
                    "status", "applied_date", "interest_rate_pa"]
            apps = [dict(zip(cols, row)) for row in cursor.fetchall()]
            conn.close()

        return {"status": "success", "customer_id": customer_id, "applications": apps}

    except Exception as exc:
        return {"status": "error", "error_message": f"Database error: {exc}"}
