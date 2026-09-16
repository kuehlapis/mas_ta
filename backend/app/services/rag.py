\
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
import numpy as np


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        p = _normalize_whitespace(p)
        if not cur:
            cur = p
            continue
        if len(cur) + 1 + len(p) <= max_chars:
            cur = f"{cur} {p}"
        else:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap > 0 else ""
            cur = (tail + " " + p).strip() if tail else p
    if cur:
        chunks.append(cur)
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
