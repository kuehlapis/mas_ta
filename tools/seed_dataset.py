\
from __future__ import annotations

import glob
import os

import requests

API = os.getenv("DOCQA_API", "http://localhost:8000/api")


def main():
    files = sorted(glob.glob("dataset/*.*"))
    print(f"Seeding {len(files)} files -> {API}")

    for fp in files:
        if fp.endswith("eval_questions.json"):
            continue
        name = os.path.basename(fp)
        with open(fp, "rb") as f:
            r = requests.post(f"{API}/documents", files={"file": (name, f, "text/plain")})
            r.raise_for_status()
            doc_id = r.json()["doc_id"]
        r2 = requests.post(f"{API}/documents/{doc_id}/ingest")
        r2.raise_for_status()
        print(f"- {name} doc_id={doc_id} chunks={r2.json()['chunks_indexed']}")

    print("Done.")


if __name__ == "__main__":
    main()
