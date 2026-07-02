"""
Prepare Lloyds Banking Group stock data as a Gemini fine-tuning dataset.

Steps:
  1. Download dataset from Kaggle
  2. Generate Q&A pairs from the OHLCV time-series
  3. Split into train (90%) / validation (10%) JSONL files
  4. Upload both files to GCS
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import kagglehub
import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv(Path(__file__).parent.parent / "bank_agent" / ".env")

KAGGLE_DATASET = "d5449344/lloyds-banking-group"
GCS_BUCKET = "ltc-hackathon"
GCS_PREFIX = "lloyds-finetune"
LOCAL_OUT = Path(__file__).parent / "data"
SYSTEM_INSTRUCTION = (
    "You are a financial analyst specialising in Lloyds Banking Group (LLOY) stock. "
    "Answer questions about historical stock price data accurately and concisely. "
    "Prices are in pence (GBX) unless stated otherwise."
)


# ---------------------------------------------------------------------------
# Dataset download
# ---------------------------------------------------------------------------

def download_dataset() -> pd.DataFrame:
    path = kagglehub.dataset_download(KAGGLE_DATASET)
    xlsx = next(Path(path).glob("*.xlsx"))
    df = pd.read_excel(xlsx, sheet_name="Market price")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    print(f"Loaded {len(df)} rows from {xlsx.name}")
    return df


# ---------------------------------------------------------------------------
# Q&A generators
# ---------------------------------------------------------------------------

def fmt_date(dt) -> str:
    return dt.strftime("%-d %B %Y")


def fmt_price(p: float) -> str:
    return f"{p:.2f}p"


def fmt_vol(v: float) -> str:
    return f"{int(v):,}"


def _qa(q: str, a: str) -> dict:
    return {
        "systemInstruction": {
            "role": "system",
            "parts": [{"text": SYSTEM_INSTRUCTION}],
        },
        "contents": [
            {"role": "user",  "parts": [{"text": q}]},
            {"role": "model", "parts": [{"text": a}]},
        ],
    }


def gen_single_day_qa(row) -> list[dict]:
    d = fmt_date(row["Date"])
    pairs = [
        _qa(
            f"What was the closing price of Lloyds (LLOY) on {d}?",
            f"The closing price of Lloyds Banking Group on {d} was {fmt_price(row['Close'])}.",
        ),
        _qa(
            f"What was the opening price of LLOY on {d}?",
            f"Lloyds Banking Group opened at {fmt_price(row['Open'])} on {d}.",
        ),
        _qa(
            f"What were the intraday high and low for Lloyds stock on {d}?",
            f"On {d} Lloyds (LLOY) hit a high of {fmt_price(row['High'])} and a low of {fmt_price(row['Low'])}.",
        ),
        _qa(
            f"How many Lloyds shares were traded on {d}?",
            f"The trading volume for Lloyds Banking Group on {d} was {fmt_vol(row['Volume'])} shares.",
        ),
        _qa(
            f"Did Lloyds stock close higher or lower than it opened on {d}?",
            (
                f"Lloyds closed {'higher' if row['Close'] >= row['Open'] else 'lower'} than it opened on {d}. "
                f"Open: {fmt_price(row['Open'])}, Close: {fmt_price(row['Close'])}."
            ),
        ),
    ]
    return pairs


def gen_range_qa(df: pd.DataFrame) -> list[dict]:
    pairs = []

    # Monthly stats
    df["YM"] = df["Date"].dt.to_period("M")
    for ym, g in df.groupby("YM"):
        label = ym.strftime("%B %Y")
        pairs += [
            _qa(
                f"What was the highest closing price for Lloyds in {label}?",
                f"The highest closing price for Lloyds (LLOY) in {label} was {fmt_price(g['Close'].max())}.",
            ),
            _qa(
                f"What was the average closing price of LLOY in {label}?",
                f"Lloyds Banking Group averaged a closing price of {fmt_price(g['Close'].mean())} in {label}.",
            ),
            _qa(
                f"What was the total trading volume for Lloyds in {label}?",
                f"Total trading volume for LLOY in {label} was {fmt_vol(g['Volume'].sum())} shares.",
            ),
        ]

    # Yearly stats
    df["Year"] = df["Date"].dt.year
    for year, g in df.groupby("Year"):
        pairs += [
            _qa(
                f"What was the highest price Lloyds stock reached in {year}?",
                f"In {year} Lloyds Banking Group hit an intraday high of {fmt_price(g['High'].max())}.",
            ),
            _qa(
                f"What was the lowest closing price for LLOY in {year}?",
                f"The lowest closing price for Lloyds in {year} was {fmt_price(g['Close'].min())}.",
            ),
            _qa(
                f"How did Lloyds stock perform overall in {year}?",
                (
                    f"Lloyds Banking Group started {year} at {fmt_price(g.iloc[0]['Open'])} and closed "
                    f"the year at {fmt_price(g.iloc[-1]['Close'])}, "
                    f"a {'gain' if g.iloc[-1]['Close'] > g.iloc[0]['Open'] else 'loss'} of "
                    f"{fmt_price(abs(g.iloc[-1]['Close'] - g.iloc[0]['Open']))}."
                ),
            ),
        ]

    return pairs


def gen_comparison_qa(df: pd.DataFrame) -> list[dict]:
    pairs = []
    rows = df.sample(min(100, len(df)), random_state=42).reset_index(drop=True)
    for i in range(0, len(rows) - 1, 2):
        r1, r2 = rows.iloc[i], rows.iloc[i + 1]
        d1, d2 = fmt_date(r1["Date"]), fmt_date(r2["Date"])
        pairs.append(_qa(
            f"How did the Lloyds closing price on {d1} compare to {d2}?",
            (
                f"On {d1} Lloyds closed at {fmt_price(r1['Close'])}; "
                f"on {d2} it closed at {fmt_price(r2['Close'])}. "
                f"That is a difference of {fmt_price(abs(r1['Close'] - r2['Close']))}."
            ),
        ))
    return pairs


# ---------------------------------------------------------------------------
# Build, split, write, upload
# ---------------------------------------------------------------------------

def build_dataset(df: pd.DataFrame) -> list[dict]:
    all_pairs: list[dict] = []
    for _, row in df.iterrows():
        all_pairs.extend(gen_single_day_qa(row))
    all_pairs.extend(gen_range_qa(df))
    all_pairs.extend(gen_comparison_qa(df))
    random.seed(42)
    random.shuffle(all_pairs)
    print(f"Generated {len(all_pairs)} Q&A pairs")
    return all_pairs


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(records)} records → {path}")


def upload_to_gcs(local_path: Path, bucket_name: str, blob_name: str) -> str:
    client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    uri = f"gs://{bucket_name}/{blob_name}"
    print(f"Uploaded → {uri}")
    return uri


def main() -> dict[str, str]:
    df = download_dataset()
    pairs = build_dataset(df)

    split = int(len(pairs) * 0.9)
    train_data, val_data = pairs[:split], pairs[split:]

    train_path = LOCAL_OUT / "train.jsonl"
    val_path   = LOCAL_OUT / "val.jsonl"
    write_jsonl(train_data, train_path)
    write_jsonl(val_data, val_path)

    train_uri = upload_to_gcs(train_path, GCS_BUCKET, f"{GCS_PREFIX}/train.jsonl")
    val_uri   = upload_to_gcs(val_path,   GCS_BUCKET, f"{GCS_PREFIX}/val.jsonl")

    uris = {"train": train_uri, "val": val_uri}
    print("\nDataset URIs:", json.dumps(uris, indent=2))
    return uris


if __name__ == "__main__":
    main()
