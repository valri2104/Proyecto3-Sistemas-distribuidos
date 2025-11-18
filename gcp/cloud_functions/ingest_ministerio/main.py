import os
import requests
from google.cloud import storage
from datetime import datetime
from flask import Request

BUCKET = os.environ.get("RAW_BUCKET")  # ejemplo: "<PREFIX>-raw-<PROJECT_ID>"
DATA_URL = os.environ.get("DATA_URL")  # url del Ministerio


def ingest_ministerio(request: Request):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET)

    resp = requests.get(DATA_URL, timeout=60)
    resp.raise_for_status()

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"ministerio/{now}.json"

    blob = bucket.blob(filename)
    blob.upload_from_string(resp.text, content_type="application/json")

    return f"Uploaded {filename} to {BUCKET}", 200
