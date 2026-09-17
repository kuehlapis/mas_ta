\
from __future__ import annotations

import glob
import mimetypes
import os

import requests

API = os.getenv("DOCQA_API", "http://localhost:8000/api")

# the eval set holds the reference answers; indexing it would leak them into retrieval
SKIP_SUFFIXES = (".json", ".jsonl")


def main():
    files = sorted(fp for fp in glob.glob("dataset/*.*") if not fp.endswith(SKIP_SUFFIXES))
    print(f"Seeding {len(files)} files -> {API}")

    for fp in files:
        name = os.path.basename(fp)
        mime = mimetypes.guess_type(name)[0] or "text/plain"
        with open(fp, "rb") as f:
            r = requests.post(f"{API}/documents", files={"file": (name, f, mime)}, timeout=300)
            r.raise_for_status()
            doc_id = r.json()["doc_id"]
        r2 = requests.post(f"{API}/documents/{doc_id}/ingest", timeout=300)
        r2.raise_for_status()
        print(f"- {name} doc_id={doc_id} chunks={r2.json()['chunks_indexed']}")

    print("Done.")


if __name__ == "__main__":
    main()
