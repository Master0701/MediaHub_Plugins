from __future__ import annotations

import re
from typing import Any

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9][A-Za-zÀ-ÖØ-öø-ÿ0-9'’&:+.-]*")
_NOISE_RE = re.compile(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9\s'’&:+.-]")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    text = _NOISE_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def text_quality(value: str) -> dict[str, Any]:
    raw = str(value or "").strip()
    normalized = normalize_text(raw)
    words = _WORD_RE.findall(normalized)
    letters = sum(character.isalpha() for character in raw)
    digits = sum(character.isdigit() for character in raw)
    visible = sum(not character.isspace() for character in raw)
    useful = letters + digits
    useful_ratio = useful / visible if visible else 0.0
    uppercase_letters = sum(character.isupper() for character in normalized)
    all_letters = sum(character.isalpha() for character in normalized)
    uppercase_ratio = (
        uppercase_letters / all_letters if all_letters else 0.0
    )

    score = 0.0
    reasons: list[str] = []

    if 1 <= len(words) <= 8:
        score += 0.24
        reasons.append("kompakte Wortanzahl")
    elif words:
        score += 0.10
        reasons.append("Text vorhanden")

    if useful_ratio >= 0.85:
        score += 0.34
        reasons.append("hoher Buchstaben-/Zahlenanteil")
    elif useful_ratio >= 0.65:
        score += 0.18
        reasons.append("brauchbarer Zeichenanteil")
    else:
        reasons.append("hoher Sonderzeichenanteil")

    if 3 <= len(normalized) <= 80:
        score += 0.18
        reasons.append("brauchbare Textlänge")

    if any(len(word) >= 3 for word in words):
        score += 0.14
        reasons.append("aussagekräftiges Wort")

    if uppercase_ratio >= 0.72 and 1 <= len(words) <= 6:
        score += 0.10
        reasons.append("logoartige Großschreibung")

    return {
        "raw": raw,
        "normalized": normalized,
        "words": words,
        "word_count": len(words),
        "useful_ratio": round(useful_ratio, 4),
        "uppercase_ratio": round(uppercase_ratio, 4),
        "score": round(min(1.0, score), 4),
        "reasons": reasons,
    }


def _nearest_frame(
    second: float,
    selected_frames: list[dict[str, Any]],
    maximum_distance: float = 1.25,
) -> dict[str, Any] | None:
    if not selected_frames:
        return None
    nearest = min(
        selected_frames,
        key=lambda item: abs(
            float(item.get("second") or 0.0) - second
        ),
    )
    if abs(float(nearest.get("second") or 0.0) - second) > maximum_distance:
        return None
    return nearest


def fuse_ocr_logo_hints(
    ocr_findings: list[dict[str, Any]] | None,
    selected_frames: list[dict[str, Any]] | None,
    duration: float,
) -> dict[str, Any]:
    """Verbindet OCR, Framequalität und Position zu Titel-/Logo-Hinweisen.

    Dies ist noch keine objektbasierte Logoerkennung. `logo_candidate`
    bedeutet: kurzer, sauberer, logoartig geschriebener Text auf einem
    hochwertigen Intro-/Outro-Frame.
    """
    selected_frames = list(selected_frames or [])
    duration = max(0.0, float(duration or 0.0))
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for finding in ocr_findings or []:
        second = round(float(finding.get("second") or 0.0), 2)
        quality = text_quality(str(finding.get("text") or ""))
        frame = _nearest_frame(second, selected_frames)

        position = (
            str(frame.get("position") or "unknown")
            if frame
            else (
                "intro"
                if duration and second <= min(180.0, duration * 0.12)
                else "outro"
                if duration and second >= max(0.0, duration - 180.0)
                else "content"
            )
        )
        frame_score = float(frame.get("score") or 0.0) if frame else 0.0
        sharpness = float(
            ((frame or {}).get("metrics") or {}).get("sharpness") or 0.0
        )
        contrast = float(
            ((frame or {}).get("metrics") or {}).get("contrast") or 0.0
        )

        score = quality["score"] * 0.56
        reasons = list(quality["reasons"])

        if frame:
            score += frame_score * 0.24
            reasons.append("mit ausgewähltem Qualitätsframe verknüpft")

        if position == "intro":
            score += 0.12
            reasons.append("Intro-/Titelkartenposition")
        elif position == "outro":
            score += 0.07
            reasons.append("Abspann-/Studioposition")

        if sharpness >= 10:
            score += 0.05
            reasons.append("scharfes Bild")
        if contrast >= 60:
            score += 0.03
            reasons.append("deutlicher Kontrast")

        score = round(min(1.0, score), 4)
        words = quality["words"]
        text_is_usable = bool(
            quality["score"] >= 0.62
            and quality["useful_ratio"] >= 0.72
            and 1 <= len(words) <= 10
            and any(
                len(word) >= 3
                and sum(character.isalpha() for character in word) >= 3
                for word in words
            )
        )

        logo_candidate = bool(
            text_is_usable
            and score >= 0.72
            and quality["uppercase_ratio"] >= 0.60
            and 1 <= len(words) <= 6
            and position in {"intro", "outro"}
        )

        normalized_text = quality["normalized"]
        normalized_casefold = normalized_text.casefold()

        # Zeit- und Handlungseinblendungen sind häufig sauber lesbarer
        # OCR-Text, aber keine Medien-/Titelidentität.
        #
        # Beispiele:
        #   "18 months earlier"
        #   "3 days later"
        #   "two years ago"
        #   "present day"
        #
        # Solche Texte dürfen daher nicht als Titelkarte in die
        # Identitätserkennung gelangen.
        narrative_time_patterns = (
            r"^(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|several|many|a|an)\s+"
            r"(?:second|seconds|minute|minutes|hour|hours|day|days|"
            r"week|weeks|month|months|year|years)\s+"
            r"(?:earlier|later|ago)$",
            r"^(?:earlier|later)\s+that\s+"
            r"(?:day|night|week|month|year)$",
            r"^(?:the\s+)?(?:next|following|previous)\s+"
            r"(?:day|night|morning|evening|week|month|year)$",
            r"^(?:present\s+day|present\s+time)$",
        )

        narrative_time_card = any(
            re.fullmatch(
                pattern,
                normalized_casefold,
                flags=re.IGNORECASE,
            )
            is not None
            for pattern in narrative_time_patterns
        )

        if narrative_time_card:
            reasons.append(
                "narrative Zeit-/Handlungseinblendung, kein Titel"
            )

        title_candidate = bool(
            text_is_usable
            and score >= 0.62
            and len(normalized_text) >= 3
            and not narrative_time_card
        )

        item = {
            "second": second,
            "text": quality["normalized"],
            "raw_text": quality["raw"],
            "score": score,
            "text_quality": quality["score"],
            "frame_score": round(frame_score, 4),
            "position": position,
            "title_candidate": title_candidate,
            "logo_candidate": logo_candidate,
            "logo_detection_mode": (
                "ocr_layout_heuristic"
                if logo_candidate
                else None
            ),
            "reasons": reasons,
            "perceptual_hashes": (
                dict(frame.get("perceptual_hashes") or {})
                if frame
                else {}
            ),
        }

        if title_candidate:
            candidates.append(item)
        else:
            item["rejection_reason"] = (
                "OCR- und Framebeleg gemeinsam zu schwach"
            )
            rejected.append(item)

    candidates.sort(
        key=lambda item: (
            item["logo_candidate"],
            item["score"],
        ),
        reverse=True,
    )

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        key = re.sub(r"[^a-z0-9]+", "", item["text"].casefold())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    best = unique[0] if unique else None

    return {
        "schema_version": 1,
        "state": "completed" if (candidates or rejected) else "no_findings",
        "method": "ocr_frame_position_fusion_v1",
        "object_logo_recognition": False,
        "candidate_count": len(unique),
        "rejected_count": len(rejected),
        "candidates": unique[:12],
        "rejected": rejected[:20],
        "best_hint": best,
        "best_title": best.get("text") if best else None,
        "best_score": best.get("score") if best else 0.0,
        "logo_candidate_count": sum(
            bool(item.get("logo_candidate")) for item in unique
        ),
        "privacy": {
            "mode": "local_only",
            "external_transfer": False,
        },
    }
