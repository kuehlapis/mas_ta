\
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
import numpy as np


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


PAGE_BREAK = "\f"


def extract_pdf_pages(data: bytes) -> list[str]:
    """Return the text of each PDF page, cleaned of layout line breaks."""
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return [_clean_pdf_text(p.extract_text() or "") for p in reader.pages]


def _clean_pdf_text(text: str) -> str:
    text = text.replace("�", "'")  # curly quotes the PDF font fails to map
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1-\2", text)  # "non-\ncompliance"
    return _normalize_whitespace(text)


def pdf_to_text(data: bytes) -> str:
    """Join pages with form feeds so ingestion can recover page numbers."""
    return PAGE_BREAK.join(extract_pdf_pages(data))


def split_pages(content: str) -> list[tuple[int, str]]:
    """(1-based page number, text) pairs; plain-text documents are a single page."""
    return [(i + 1, p) for i, p in enumerate(content.split(PAGE_BREAK)) if p.strip()]


def _sentences(text: str, max_chars: int) -> list[str]:
    units: list[str] = []
    for s in re.split(r"(?<=[.!?])\s+", _normalize_whitespace(text)):
        while len(s) > max_chars:  # no sentence boundary (tables, infographics): cut on a word
            cut = s.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            units.append(s[:cut])
            s = s[cut:].strip()
        if s:
            units.append(s)
    return units


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Pack sentences into chunks of up to max_chars, repeating trailing sentences
    (up to `overlap` chars) at the start of the next chunk."""
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for s in _sentences(text, max_chars):
        if cur and cur_len + 1 + len(s) > max_chars:
            chunks.append(" ".join(cur))
            tail: list[str] = []
            for prev in reversed(cur):
                if sum(len(t) + 1 for t in tail) + len(prev) > overlap:
                    break
                tail.insert(0, prev)
            cur, cur_len = tail, sum(len(t) + 1 for t in tail)
            while cur and cur_len + len(s) > max_chars:  # overlap must not push past the limit
                cur_len -= len(cur.pop(0)) + 1
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def tokenize(s: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", s.lower())


def embed_hash(text: str, *, dim: int = 384) -> np.ndarray:
    v = np.zeros((dim,), dtype=np.float32)
    for tok in tokenize(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = -1.0 if (h >> 8) & 1 else 1.0
        v[idx] += sign
    norm = float(np.linalg.norm(v))
    if norm > 0:
        v /= norm
    return v


def rrf(rank: int, *, k: int = 60) -> float:
    return 1.0 / (k + rank + 1)


@dataclass(frozen=True)
class ScoredChunk:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    page: int = 1
    filename: str = ""
