\
from __future__ import annotations

import pymupdf
import pymupdf4llm
import hashlib
import re
from dataclasses import dataclass
import numpy as np
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


PAGE_BREAK = "\f"

MAX_CHUNK_CHARS = 1500
CHUNK_OVERLAP = 150
MIN_SECTION_CHARS = 200  # smaller sections (usually a lone heading) are merged into the next one

_HEADERS = [("#" * i, f"h{i}") for i in range(1, 7)]


def pdf_to_text(data: bytes) -> str:
    """Convert a PDF to Markdown per page, joined with form feeds so ingestion
    can recover page numbers."""

    with pymupdf.open(stream=data, filetype="pdf") as doc:
        pages = pymupdf4llm.to_markdown(doc, page_chunks=True, show_progress=False)
    return PAGE_BREAK.join(_clean_markdown(p["text"]) for p in pages)


def _clean_markdown(md: str) -> str:
    md = md.replace("�", "'")  # curly quotes the PDF font fails to map
    md = re.sub(r"<!-- (Start|End) of picture text -->", "", md)
    md = md.replace("<br>", " ")
    md = re.sub(r"^[ \t]*\d{1,3}[ \t]*$", "", md, flags=re.M)  # page-number footer lines
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def split_pages(content: str) -> list[tuple[int, str]]:
    """(1-based page number, text) pairs; plain-text documents are a single page."""
    return [(i + 1, p) for i, p in enumerate(content.split(PAGE_BREAK)) if p.strip()]


def _heading_text(h: str) -> str:
    return _normalize_whitespace(re.sub(r"<[^>]+>|[*_`]", "", h))


def chunk_text(text: str) -> list[str]:
    """Split one page of Markdown into chunks.

    1. MarkdownHeaderTextSplitter cuts the page into sections at headings.
    2. Sections shorter than MIN_SECTION_CHARS are merged into the following one.
    3. RecursiveCharacterTextSplitter caps each section at MAX_CHUNK_CHARS.
    4. Each chunk is prefixed with "[page title > section heading]" so a chunk from
       the middle of a section still carries its topic for BM25 and embeddings.
    """

    sections = MarkdownHeaderTextSplitter(_HEADERS, strip_headers=False).split_text(text)
    headed = [
        (_heading_text(next(reversed(s.metadata.values()), "")), s.page_content.strip())
        for s in sections
        if s.page_content.strip()
    ]
    if not headed:
        return []

    merged: list[tuple[str, str]] = []
    carry = ""
    for heading, body in headed:
        body = f"{carry}\n\n{body}" if carry else body
        if len(body) < MIN_SECTION_CHARS:
            carry = body
            continue
        carry = ""
        merged.append((heading, body))
    if carry:  # short trailing section: attach to the previous one, or keep alone
        if merged:
            merged[-1] = (merged[-1][0], f"{merged[-1][1]}\n\n{carry}")
        else:
            merged.append((headed[-1][0], carry))

    page_title = headed[0][0]
    chunks: list[str] = []
    for heading, body in merged:
        crumbs = [c for c in dict.fromkeys([page_title, heading]) if c]
        prefix = f"[{' > '.join(crumbs)}]\n" if crumbs else ""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max(MAX_CHUNK_CHARS - len(prefix), 500), chunk_overlap=CHUNK_OVERLAP
        )
        chunks += [prefix + part for part in splitter.split_text(body)]
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
    keyword_rank: int | None = None  # 1-based position in the Elasticsearch results
    semantic_rank: int | None = None  # 1-based position in the Redis KNN results


def split_section(text: str) -> tuple[str, str]:
    """Separate the "[page title > section]" line that chunk_text prepends."""
    m = re.match(r"\[([^\]\n]*)\]\n", text)
    return (m.group(1), text[m.end():]) if m else ("", text)
