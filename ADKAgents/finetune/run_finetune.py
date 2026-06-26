"""
Launch a Gemini supervised fine-tuning job on Vertex AI.

Usage:
    uv run python finetune/run_finetune.py            # prepare data + start tuning
    uv run python finetune/run_finetune.py --status   # check status of latest job
    uv run python finetune/run_finetune.py --no-prep  # skip data prep, just start tuning
"""

import argparse
import json
import os
import sys
from pathlib import Path

import vertexai
from dotenv import load_dotenv
from vertexai.preview.tuning import sft

load_dotenv(Path(__file__).parent.parent / "bank_agent" / ".env")

PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT", "ltc-ipnihack-prj-11")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET = "ltc-hackathon"
GCS_PREFIX = "lloyds-finetune"
BASE_MODEL = "gemini-1.5-flash-002"
TUNED_MODEL_NAME = "lloyds-banking-gemini"
JOB_RECORD = Path(__file__).parent / "data" / "last_job.json"


def prepare_data() -> dict[str, str]:
    # Import lazily so --status skips the heavy Kaggle download
    from prepare_dataset import main as prep_main
    return prep_main()


def start_tuning(train_uri: str, val_uri: str) -> sft.SupervisedTuningJob:
    vertexai.init(project=PROJECT, location=LOCATION)

    print(f"\nStarting supervised fine-tuning job on {BASE_MODEL} …")
    job = sft.train(
        source_model=BASE_MODEL,
        train_dataset=train_uri,
        validation_dataset=val_uri,
        epochs=3,
        learning_rate_multiplier=1.0,
        tuned_model_display_name=TUNED_MODEL_NAME,
    )
    print(f"Job name  : {job.name}")
    print(f"Job state : {job.state}")

    JOB_RECORD.parent.mkdir(parents=True, exist_ok=True)
    JOB_RECORD.write_text(json.dumps({
        "job_name": job.name,
        "train_uri": train_uri,
        "val_uri":   val_uri,
    }, indent=2))
    print(f"\nJob details saved → {JOB_RECORD}")
    return job


def check_status() -> None:
    if not JOB_RECORD.exists():
        print("No job record found. Run without --status first.")
        sys.exit(1)

    record = json.loads(JOB_RECORD.read_text())
    vertexai.init(project=PROJECT, location=LOCATION)

    job = sft.SupervisedTuningJob(record["job_name"])
    print(f"Job name  : {job.name}")
    print(f"Job state : {job.state}")
    if hasattr(job, "tuned_model_name") and job.tuned_model_name:
        print(f"Tuned model: {job.tuned_model_name}")
        print("\nTo use this model in your agent, set GEMINI_MODEL to the tuned model name above.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status",  action="store_true", help="Check status of latest job")
    parser.add_argument("--no-prep", action="store_true", help="Skip dataset preparation")
    args = parser.parse_args()

    if args.status:
        check_status()
        return

    if args.no_prep:
        if not JOB_RECORD.exists():
            print("No previous job record. Cannot skip prep without existing URIs.")
            sys.exit(1)
        record = json.loads(JOB_RECORD.read_text())
        uris = {"train": record["train_uri"], "val": record["val_uri"]}
    else:
        uris = prepare_data()

    job = start_tuning(uris["train"], uris["val"])

    print("\n" + "=" * 60)
    print("Fine-tuning job submitted successfully.")
    print(f"  Base model    : {BASE_MODEL}")
    print(f"  Train dataset : {uris['train']}")
    print(f"  Val dataset   : {uris['val']}")
    print(f"  Job name      : {job.name}")
    print("=" * 60)
    print("Training takes ~1-3 hours. Run with --status to check progress.")
    print("=" * 60)


if __name__ == "__main__":
    main()
