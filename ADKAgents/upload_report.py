"""Upload a local directory to a GCS bucket under a given prefix.

Usage: python upload_report.py <bucket> <local_dir> <prefix>
Bucket objects are made publicly readable after upload.
"""
import sys
import mimetypes
from pathlib import Path

from google.cloud import storage


def upload(bucket_name: str, local_dir: str, prefix: str) -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    base = Path(local_dir)

    files = [f for f in base.rglob("*") if f.is_file()]
    print(f"Uploading {len(files)} files to gs://{bucket_name}/{prefix}/")

    for f in files:
        blob_name = f"{prefix}/{f.relative_to(base).as_posix()}"
        content_type, _ = mimetypes.guess_type(str(f))
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(f), content_type=content_type or "application/octet-stream")
        blob.make_public()

    print(f"Done. Public URL: https://storage.googleapis.com/{bucket_name}/{prefix}/index.html")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: upload_report.py <bucket> <local_dir> <prefix>")
        sys.exit(1)
    upload(sys.argv[1], sys.argv[2], sys.argv[3])
