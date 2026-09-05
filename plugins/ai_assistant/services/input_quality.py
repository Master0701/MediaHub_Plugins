from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Any

_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9'’-]*")
_COMMON_SHORT = {"der", "die", "das", "the", "and", "und", "von", "of", "in", "im", "am", "an", "zu", "a", "i"}

@dataclass(frozen=True, slots=True)
class TextQuality:
    score: float
    accepted: bool
    reasons: tuple[str, ...]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def evaluate_text(value: str, *, source: str = "unknown", known_alias: bool = False) -> TextQuality:
    text = str(value or "").strip()
    words = _WORD_RE.findall(text)
    alpha = sum(c.isalpha() for c in text)
    alnum = sum(c.isalnum() for c in text)
    visible = sum(not c.isspace() for c in text)
    special = max(0, visible - alnum)
    alpha_ratio = alpha / max(1, visible)
    special_ratio = special / max(1, visible)
    meaningful = [w for w in words if len(w) >= 2 and w.casefold() not in _COMMON_SHORT]
    avg_len = sum(len(w) for w in words) / max(1, len(words))

    short_fragments = [
        word
        for word in words
        if len(word) <= 2
    ]

    short_fragment_ratio = (
        len(short_fragments) / len(words)
        if words
        else 0.0
    )

    # OCR-Zeichensalat besteht häufig aus vielen formal gültigen
    # Buchstabenfragmenten wie:
    #
    #   "ET id ur eo ... N owl ... BR N UN ..."
    #
    # Dadurch können Buchstabenanteil und Wortanzahl irreführend gut
    # aussehen. Dieser Filter gilt nur für längere OCR-Ausgaben.
    # Kurze echte Titel bleiben ausdrücklich unberührt.
    ocr_fragment_noise = bool(
        source == "ocr"
        and len(words) >= 8
        and (
            short_fragment_ratio >= 0.55
            or (
                len(words) >= 12
                and avg_len < 2.35
            )
        )
    )

    score = 0.0
    reasons: list[str] = []
    if known_alias:
        score += 0.62
        reasons.append("Lokaler Wissens- oder Aliasbeleg")
    if len(words) >= 2:
        score += 0.22
    elif len(words) == 1 and len(words[0]) >= 5:
        score += 0.10
        reasons.append("Nur ein einzelnes Wort")
    if len(meaningful) >= 2:
        score += 0.20
    elif len(meaningful) == 1:
        score += 0.08
    if alpha_ratio >= 0.72:
        score += 0.22
    elif alpha_ratio >= 0.50:
        score += 0.10
    else:
        reasons.append("Zu geringer Buchstabenanteil")
    if special_ratio <= 0.10:
        score += 0.14
    elif special_ratio > 0.25:
        score -= 0.25
        reasons.append("Zu viele Sonderzeichen")
    if 2.5 <= avg_len <= 18:
        score += 0.10
    if len(normalize_key(text).replace(" ", "")) < 4:
        score -= 0.35
        reasons.append("Zu wenig verwertbarer Text")

    # OCR must be stricter than filenames; aliases remain trusted.
    threshold = 0.58 if source == "ocr" else 0.48
    if source == "fallback":
        threshold = 0.62

    if ocr_fragment_noise:
        score -= 0.45
        reasons.append(
            "OCR enthält zu viele kurze Textfragmente"
        )

    score = max(0.0, min(1.0, score))

    accepted = (
        known_alias
        or (
            score >= threshold
            and not ocr_fragment_noise
        )
    )
    if accepted:
        reasons.append("Qualitätsgrenze erreicht")
    else:
        reasons.append("Unter Qualitätsgrenze verworfen")
    return TextQuality(round(score, 4), accepted, tuple(dict.fromkeys(reasons)), {
        "word_count": len(words), "meaningful_words": len(meaningful),
        "alpha_ratio": round(alpha_ratio, 4), "special_ratio": round(special_ratio, 4),
        "average_word_length": round(avg_len, 2),
        "short_fragment_ratio": round(short_fragment_ratio, 4),
        "ocr_fragment_noise": ocr_fragment_noise,
        "source": source,
    })
