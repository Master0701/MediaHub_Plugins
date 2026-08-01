from __future__ import annotations
import re
import uuid
from typing import Any


class SemanticFieldClassifier:
    @staticmethod
    def _sentences(text: str) -> list[str]:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    def classify(self, *, title: str, text: str, semantic_result=None, parser_result=None):
        title = self._norm(title)
        semantic_result = dict(semantic_result or {})
        parser_result = dict(parser_result or {})
        fields = {}
        rejected = []

        def add(name, value, confidence, sentence, reason):
            fields.setdefault(name, []).append({
                "id": uuid.uuid4().hex,
                "field": name,
                "value": value,
                "confidence": round(float(confidence), 4),
                "sentence": sentence,
                "reason": reason,
                "requires_confirmation": True,
            })

        for sentence in self._sentences(text):
            low = sentence.casefold()

            if any(x in low for x in ("cosplay", "poster", "cover", "screenshot", "logo", "artwork")):
                match = re.search(r"\b(19\d{2}|20\d{2})\b", sentence)
                if match:
                    rejected.append({
                        "field": "year",
                        "value": int(match.group(1)),
                        "sentence": sentence,
                        "reason": "Bild- oder Artwork-Kontext.",
                    })
                continue

            match = re.search(
                r"(?i)(?:fortsetzung|nachfolger)\s+von\s+(.+?)(?:\s+aus dem jahr\s+(19\d{2}|20\d{2}))?[.]?$",
                sentence,
            )
            if match:
                add(
                    "predecessor",
                    {"title": self._norm(match.group(1)), "year": int(match.group(2)) if match.group(2) else None},
                    0.92,
                    sentence,
                    "Satz nennt ausdrücklich einen Vorgänger.",
                )

            patterns = (
                ("release_year", r"(?i)erscheinungsjahr\s+(19\d{2}|20\d{2})", 0.96),
                ("release_year", r"(?i)am\s+\d{1,2}\.\s+\w+\s+(19\d{2}|20\d{2})\s+erschienen", 0.95),
                ("planned_release_year", r"(?i)sollte ursprünglich.*?\b(19\d{2}|20\d{2})\b", 0.84),
                ("production_year", r"(?i)(?:produktion|vorproduktion|dreharbeiten).*?\b(19\d{2}|20\d{2})\b", 0.78),
                ("universe_transition_year", r"(?i)universe.*?\b(19\d{2}|20\d{2})\b.*?ersetzt", 0.82),
            )
            for name, pattern, confidence in patterns:
                m = re.search(pattern, sentence)
                if m:
                    add(name, int(m.group(1)), confidence, sentence, f"Satzmuster für {name}.")
                    break

        for entity in semantic_result.get("entity_proposals") or []:
            if (
                self._norm(entity.get("title")).casefold() == title.casefold()
                and entity.get("entity_type") == "movie"
                and entity.get("year") is not None
            ):
                add(
                    "release_year",
                    int(entity["year"]),
                    float(entity.get("confidence") or 0.89),
                    str(entity.get("sentence") or ""),
                    "Semantic Engine ordnet Jahr dem Hauptfilm zu.",
                )

        parser_fields = (parser_result.get("result") or {}).get("fields") or {}
        universe = self._norm((parser_fields.get("metadata") or {}).get("universe"))
        if universe:
            add("universe", universe, 0.86, "", "Parser erkannte das Medienuniversum.")

        dedup = {}
        for name, items in fields.items():
            seen = set()
            dedup[name] = []
            for item in sorted(items, key=lambda x: -float(x["confidence"])):
                key = repr(item["value"])
                if key in seen:
                    continue
                seen.add(key)
                dedup[name].append(item)

        return {
            "schema_version": 1,
            "strategy": "semantic_field_classifier_v280",
            "title": title,
            "fields": dedup,
            "primary_values": {k: v[0]["value"] for k, v in dedup.items() if v},
            "rejected": rejected,
            "automatic_import": False,
            "requires_confirmation": True,
        }
