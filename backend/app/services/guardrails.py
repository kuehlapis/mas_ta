\

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|earlier|all|any|system|safety)\b.{0,20}\b(instructions?|prompts?|rules|guidelines|messages?|context)\b",
    r"\b(new|updated|real|actual|hidden)\s+(instructions?|system\s+prompt|rules)\b",
    r"\bsystem\s*prompt\b",
    r"\byou\s+are\s+(now|no\s+longer|actually)\b",
    r"\b(act|behave|respond|pretend)\s+(as|like)\s+(if\s+)?(an?\s+)?(ai|assistant|chatbot|language\s+model|dan|developer)\b",
    r"\b(as\s+an?|to\s+the)\s+(ai|assistant|chatbot|language\s+model|llm)\b",
    r"\b(respond|reply|answer)\s+(only\s+)?(with|by\s+saying|that)\b",
    r"\b(reveal|print|output|leak|show)\b.{0,30}\b(prompt|instructions|api\s*keys?|secrets?|password|credentials)\b",
    r"\bjailbreak\b|\bdeveloper\s+mode\b|\bdo\s+anything\s+now\b",
    r"<\s*/?\s*(system|assistant|user|instructions?)\s*>",
    r"\[\s*(system|inst)\s*\]",
]
_INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)


def is_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))
