\
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.services.guardrails import is_injection
from app.services.rag import ScoredChunk, split_section, tokenize

NO_ANSWER = "I don't know based on the provided documents."
REDACTED = "[removed: suspected prompt injection]"

MAX_PASSAGE_SENTENCES = 3
PASSAGE_SIZE_PENALTY = 0.06  # per extra sentence, so longer passages must add real coverage
MIN_QUERY_COVERAGE = 0.3  # share of the question's (IDF-weighted) terms the best sentence must contain
SNIPPET_CHARS = 300

_STOPWORDS = set(
    """a an the of and or to in on at by for with from as is are was were be been being what which who whom
    whose how when where why that this these those it its into during there their his her he she they them do
    does did has have had not no any all such than then so if about under over mentioned much many
    give given get got can could would should will shall may might""".split()
)
_ABBREVIATIONS = re.compile(r"\b(Mr|Ms|Mrs|Dr|Pte|Ltd|Co|Inc|No|St|Bhd|Corp|vs|e\.g|i\.e)\.$", re.IGNORECASE)
_QUANTITY_QUESTION = re.compile(r"\b(how\s+(many|much|long)|total|number|amount|value|average|percentage)\b", re.I)


def to_plain(markdown: str) -> str:
    """Markdown chunk body -> readable plain text (one sentence group per line)."""
    lines = []
    for ln in markdown.splitlines():
        if re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", ln):  # table separator row
            continue
        if ln.strip().startswith("|"):  # table row -> "cell: cell"
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            ln = ": ".join(c for c in cells if c)
        ln = re.sub(r"<[^>]+>", "", ln)
        ln = re.sub(r"^\s*(#{1,6}|>|[-*+]|\d+\.)\s+", "", ln)
        ln = re.sub(r"[*_`]+", "", ln)
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return "\n".join(lines)


def _split_sentences(line: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[$])", line)
    out: list[str] = []
    buf = ""
    for p in parts:
        buf = f"{buf} {p}".strip() if buf else p
        if not _ABBREVIATIONS.search(buf):
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


@dataclass
class _Unit:
    text: str  # a sentence or table row, verbatim from to_plain() output
    heading: str  # nearest heading above it, used as context when scoring


def _units(markdown: str) -> list[_Unit]:
    """Sentences with the heading they sit under. Heading lines only become answer
    candidates when they carry a figure (infographic facts like "33 Criminal Convictions")."""
    units: list[_Unit] = []
    heading = ""
    for raw in markdown.splitlines():
        is_heading = bool(re.match(r"\s*#{1,6}\s", raw)) or bool(re.fullmatch(r"\s*\*\*[^*]+\*\*\s*", raw))
        line = to_plain(raw)
        if not line:
            continue
        if is_heading:
            heading = line
            if not re.search(r"\d", line):
                continue
        units += [_Unit(x, heading) for x in _split_sentences(line) if len(tokenize(x)) >= 2]
    return units


def _stem(t: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(t) > len(suffix) + 3 and t.endswith(suffix):
            return t[: -len(suffix)]
    return t[:-1] if len(t) > 4 and t.endswith("e") else t


def _terms(text: str) -> set[str]:
    return {_stem(t) for t in tokenize(text) if t not in _STOPWORDS}


@dataclass
class Citation:
    n: int
    chunk: ScoredChunk
    section: str
    plain: str
    quotes: list[str]

    def snippet(self) -> str:
        """A window of the chunk that contains every quoted sentence."""
        starts = [self.plain.find(q) for q in self.quotes]
        ends = [s + len(q) for s, q in zip(starts, self.quotes)]
        lo, hi = min(starts), max(ends)
        pad = max(0, SNIPPET_CHARS - (hi - lo)) // 2
        lo, hi = max(0, lo - pad), min(len(self.plain), hi + pad)
        text = self.plain[lo:hi].replace("\n", " ")
        return ("…" if lo > 0 else "") + text + ("…" if hi < len(self.plain) else "")


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    blocked_sentences: int


def answer_question(question: str, chunks: list[ScoredChunk]) -> Answer:
    q_terms = _terms(question)
    if not chunks or not q_terms:
        return Answer(NO_ANSWER, [], 0)

    # sentences of every retrieved chunk, in document order
    per_chunk: list[tuple[str, str, list[_Unit]]] = []  # (section, plain chunk text, safe units)
    blocked = 0
    for c in chunks:
        section, body = split_section(c.text)
        plain = to_plain(body)
        units = _units(body)
        flagged = {u.text for u in units if is_injection(u.text)}
        for f in flagged:  # don't display injected text in citations either
            plain = plain.replace(f, REDACTED)
        blocked += len(flagged)
        per_chunk.append((section, plain, [u for u in units if u.text not in flagged]))
    if not any(units for _, _, units in per_chunk):
        return Answer(NO_ANSWER, [], blocked)

    # IDF over sentences: words that appear everywhere ("mas", "cases") count less
    all_units = [u for _, _, units in per_chunk for u in units]
    df: dict[str, int] = {}
    for u in all_units:
        for t in _terms(u.text):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + len(all_units) / df.get(t, 0.5)) for t in q_terms}
    total = sum(idf.values())
    wants_number = bool(_QUANTITY_QUESTION.search(question))

    # score passages of 1..MAX_PASSAGE_SENTENCES consecutive sentences, so a sentence like
    # "He was sentenced to 68 months" can borrow "Mr Loh" from the sentence before it
    best = None  # (score, coverage, chunk index, [sentences])
    for i, (section, plain, units) in enumerate(per_chunk):
        section_terms = _terms(section)
        for start in range(len(units)):
            for size in range(1, MAX_PASSAGE_SENTENCES + 1):
                window = units[start : start + size]
                if len(window) < size:
                    break
                text_terms = set().union(*(_terms(u.text) for u in window))
                context_terms = (set().union(*(_terms(u.heading) for u in window)) | section_terms) - text_terms
                match = sum(idf[t] for t in q_terms & text_terms) + 0.5 * sum(idf[t] for t in q_terms & context_terms)
                coverage = match / total
                score = coverage - PASSAGE_SIZE_PENALTY * (size - 1) - 0.01 * i
                if wants_number and any(re.search(r"\d", u.text) for u in window):
                    score += 0.1
                if best is None or score > best[0]:
                    best = (score, coverage, i, [u.text for u in window])

    if best is None or best[1] < MIN_QUERY_COVERAGE:
        return Answer(NO_ANSWER, [], blocked)

    _, _, i, sentences = best
    section, plain, _ = per_chunk[i]
    # headings/table rows have no closing punctuation; separate them so the quote stays readable
    passage = " ".join(x if re.search(r"[.!?:;]$", x) else f"{x}." for x in sentences)
    citation = Citation(n=1, chunk=chunks[i], section=section, plain=plain, quotes=sentences)
    return Answer(f"{passage} [1]", [citation], blocked)
