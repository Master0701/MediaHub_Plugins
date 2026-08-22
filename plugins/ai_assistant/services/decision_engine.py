from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, ClassVar


class DecisionEngine:
    """Führt unabhängige Agentenbeweise zu einer nachvollziehbaren Entscheidung zusammen."""

    def __init__(self, fingerprint_store=None):
        self.fingerprint_store = fingerprint_store

    SOURCE_WEIGHTS: ClassVar[dict[str, float]] = {
        "filename": 0.58,
        "folder": 0.48,
        "online": 0.72,
        "ocr": 0.78,
        "subtitle": 0.72,
        "fingerprint": 0.98,
        "technical": 0.30,
        "scene": 0.24,
        "audio": 0.20,
    }

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        online = analysis.get("online") or {}
        in_video = analysis.get("in_video") or {}
        agents = in_video.get("agents") or {}

        title = str(identification.get("title_candidate") or "").strip()
        normalized_title = self._normalize(title)
        local_confidence = self._clamp(float(identification.get("confidence") or 0.0))

        evidence: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []

        if title:
            evidence.append(self._item(
                source="filename",
                label="Dateiname",
                value=title,
                confidence=local_confidence,
                supports=True,
                detail="Titel- und Episodenmuster aus Datei- oder Ordnernamen.",
            ))

        ranking = online.get("ranking") or {}
        best = ranking.get("best_match") or {}
        if best:
            candidate = str(best.get("title") or "").strip()
            candidate_conf = self._clamp(float(best.get("score") or 0.0))

            candidate_titles = [
                candidate,
                str(best.get("original_title") or "").strip(),
                *[
                    str(alias or "").strip()
                    for alias in (best.get("aliases") or [])
                ],
            ]

            candidate_similarities = [
                self._similarity(
                    normalized_title,
                    self._normalize(candidate_title),
                )
                for candidate_title in candidate_titles
                if title and candidate_title
            ]

            similarity = (
                max(candidate_similarities)
                if candidate_similarities
                else 0.0
            )

            normalized_aliases = {
                self._normalize(alias)
                for alias in (best.get("aliases") or [])
                if str(alias or "").strip()
            }

            exact_alias_match = bool(
                normalized_title
                and normalized_title in normalized_aliases
            )

            ranking_decision = str(ranking.get("decision") or "").strip().lower()
            penalties = {str(item) for item in (best.get("penalties") or [])}
            evidence_count = int(best.get("evidence_count") or 0)
            blocking_penalties = {
                "weak_single_word_variant",
                "insufficient_combined_evidence",
            }

            # Einwort-Titel wie "Chappie" dürfen nicht allein deshalb
            # verworfen werden, weil sie aus nur einem Wort bestehen.
            #
            # Die Ausnahme gilt ausschließlich dann, wenn mindestens
            # zwei unterschiedliche Online-Provider exakt denselben
            # Titel wie der lokale Titelkandidat liefern.
            provider_results = list(
                online.get("provider_results") or []
            )

            exact_title_providers: set[str] = set()

            for provider_result in provider_results:
                provider_id = str(
                    provider_result.get("provider_id")
                    or provider_result.get("provider_name")
                    or ""
                ).strip()

                matches = (
                    provider_result.get("matches")
                    or provider_result.get("results")
                    or []
                )

                if isinstance(matches, dict):
                    matches = [matches]

                for match in matches:
                    if not isinstance(match, dict):
                        continue

                    match_title = self._normalize(
                        str(match.get("title") or "")
                    )

                    if (
                        normalized_title
                        and match_title == normalized_title
                    ):
                        if provider_id:
                            exact_title_providers.add(provider_id)
                        break

            multi_provider_exact_match = (
                len(exact_title_providers) >= 2
            )

            effective_blocking_penalties = set(
                blocking_penalties
            )

            if multi_provider_exact_match:
                effective_blocking_penalties.discard(
                    "weak_single_word_variant"
                )
                effective_blocking_penalties.discard(
                    "insufficient_combined_evidence"
                )

            normal_online_confirmation = (
                ranking_decision
                in {"probable_match", "strong_match"}
                and candidate_conf >= 0.65
                and evidence_count >= 2
                and not penalties.intersection(
                    effective_blocking_penalties
                )
                and similarity >= 0.45
            )

            multi_provider_confirmation = (
                multi_provider_exact_match
                and similarity >= 0.95
            )

            identity_supported = (
                normal_online_confirmation
                or multi_provider_confirmation
            )
            if identity_supported:
                if multi_provider_confirmation:
                    detail = (
                        "Mehrere unabhängige Online-Provider bestätigen "
                        "denselben exakten Titel; "
                        f"{len(exact_title_providers)} Provider und "
                        f"Titelähnlichkeit "
                        f"{round(similarity * 100)} %."
                    )
                else:
                    if exact_alias_match:
                        detail = (
                            "Online-Treffer bestätigt die Identität "
                            "über einen offiziellen Alternativtitel; "
                            f"Ranking {ranking_decision}, "
                            f"{evidence_count} Belege und "
                            f"Titelähnlichkeit "
                            f"{round(similarity * 100)} %."
                        )
                    else:
                        detail = (
                            "Online-Treffer bestätigt die Identität; "
                            f"Ranking {ranking_decision}, "
                            f"{evidence_count} Belege und "
                            f"Titelähnlichkeit "
                            f"{round(similarity * 100)} %."
                        )
            else:
                blockers: list[str] = []
                if ranking_decision not in {"probable_match", "strong_match"}:
                    blockers.append(f"Ranking-Entscheidung {ranking_decision or 'unbekannt'}")
                if candidate_conf < 0.65:
                    blockers.append(f"Score nur {round(candidate_conf * 100)} %")
                if evidence_count < 2:
                    blockers.append("zu wenig kombinierte Belege")
                if penalties.intersection(blocking_penalties):
                    blockers.append("gesperrte Strafwerte: " + ", ".join(sorted(penalties.intersection(blocking_penalties))))
                detail = (
                    "Online-Treffer gefunden, aber nicht als Identitätsbestätigung verwendet"
                    + (": " + "; ".join(blockers) if blockers else ".")
                )
            online_evidence_confidence = candidate_conf

            if multi_provider_confirmation:
                provider_confidences: list[float] = []

                for provider_result in provider_results:
                    provider_id = str(
                        provider_result.get("provider_id")
                        or provider_result.get("provider_name")
                        or ""
                    ).strip()

                    if provider_id not in exact_title_providers:
                        continue

                    matches = (
                        provider_result.get("matches")
                        or provider_result.get("results")
                        or []
                    )

                    if isinstance(matches, dict):
                        matches = [matches]

                    for match in matches:
                        if not isinstance(match, dict):
                            continue

                        match_title = self._normalize(
                            str(match.get("title") or "")
                        )

                        if match_title != normalized_title:
                            continue

                        try:
                            provider_confidence = float(
                                match.get("provider_confidence")
                                or 0.0
                            )
                        except (TypeError, ValueError):
                            provider_confidence = 0.0

                        if provider_confidence > 0:
                            provider_confidences.append(
                                self._clamp(provider_confidence)
                            )

                        break

                if provider_confidences:
                    online_evidence_confidence = (
                        sum(provider_confidences)
                        / len(provider_confidences)
                    )
                else:
                    # Mehrere unabhängige exakte Provider-Treffer
                    # sind auch ohne expliziten Provider-Confidence-
                    # Wert deutlich stärker als der durch die
                    # Einwort-Strafe reduzierte Ranking-Score.
                    online_evidence_confidence = max(
                        candidate_conf,
                        0.82,
                    )

            evidence.append(self._item(
                source="online",
                label=str(best.get("provider_name") or "Online"),
                value=candidate,
                confidence=online_evidence_confidence,
                supports=identity_supported,
                detail=detail,
            ))
            if title and similarity < 0.35 and candidate_conf >= 0.65:
                conflicts.append(self._conflict("title", "Dateiname", title, "Online", candidate, "hoch"))

        subtitle = agents.get("subtitle_agent") or {}
        subtitle_tokens = list(subtitle.get("proper_names") or []) + list(subtitle.get("keywords") or [])
        subtitle_match = self._best_token_match(normalized_title, subtitle_tokens)
        if subtitle.get("state") == "completed":
            evidence.append(self._item(
                source="subtitle",
                label="Untertitel",
                value=subtitle_match[1] or f"{subtitle.get('characters', 0)} Zeichen ausgewertet",
                confidence=subtitle_match[0] if subtitle_match[1] else 0.30,
                supports=bool(subtitle_match[1] and subtitle_match[0] >= 0.50),
                detail=(
                    f"Titelähnlicher Begriff in Untertiteln gefunden ({round(subtitle_match[0] * 100)} %)."
                    if subtitle_match[1]
                    else "Untertitel wurden ausgewertet, enthielten aber noch keinen eindeutigen Titelbeleg."
                ),
            ))

        ocr = agents.get("ocr_agent") or {}
        ocr_texts = [str(item.get("text") or "") for item in (ocr.get("findings") or [])]
        ocr_match = self._best_token_match(normalized_title, ocr_texts)
        if ocr.get("state") == "completed":
            evidence.append(self._item(
                source="ocr",
                label="OCR",
                value=ocr_match[1] or f"{len(ocr_texts)} Textfunde",
                confidence=ocr_match[0] if ocr_match[1] else 0.24,
                supports=bool(ocr_match[1] and ocr_match[0] >= 0.52),
                detail=(
                    f"Titelähnlicher Bildtext erkannt ({round(ocr_match[0] * 100)} %)."
                    if ocr_match[1]
                    else "Bildtexte wurden erkannt, bestätigen den Titel aber noch nicht eindeutig."
                ),
            ))

        fingerprint = agents.get("fingerprint_agent") or {}
        if fingerprint.get("state") == "completed":
            matched_identity = fingerprint.get("matched_identity")
            fingerprint_value = fingerprint.get("video_fingerprint")
            if not matched_identity and self.fingerprint_store is not None:
                matched_identity = self.fingerprint_store.lookup(fingerprint_value)
                if matched_identity:
                    fingerprint["matched_identity"] = matched_identity
            evidence.append(self._item(
                source="fingerprint",
                label="Fingerprint",
                value=self._identity_label(matched_identity) if matched_identity else str(fingerprint.get("video_fingerprint") or "erstellt")[:80],
                confidence=0.99 if matched_identity else 0.35,
                supports=bool(matched_identity),
                detail=(
                    "Fingerprint stimmt mit einem bekannten Medium überein."
                    if matched_identity
                    else "Fingerprint wurde erstellt; ein bekannter Vergleichstreffer fehlt noch."
                ),
            ))

        technical_support = 0.0
        summary = analysis.get("summary") or {}
        if identification.get("media_type") == "series":
            if identification.get("season") is not None and identification.get("episodes"):
                technical_support += 0.55
            duration = float(summary.get("duration_seconds") or 0.0)
            if 900 <= duration <= 7200:
                technical_support += 0.25
        if technical_support:
            evidence.append(self._item(
                source="technical",
                label="Technische Daten",
                value="Laufzeit, Staffel/Folge und Streamstruktur",
                confidence=min(0.80, technical_support),
                supports=True,
                detail="Technische Merkmale sind mit dem vorgeschlagenen Medientyp vereinbar.",
            ))

        decision_confidence, support_strength, independence = self._combine(evidence)
        contradiction_penalty = min(0.35, sum(0.16 if c["severity"] == "hoch" else 0.08 for c in conflicts))
        final_confidence = self._clamp(decision_confidence - contradiction_penalty)

        confirmed = [item for item in evidence if item["supports"] and item["weighted_score"] >= 0.22]
        weak = [item for item in evidence if not item["supports"] or item["weighted_score"] < 0.22]

        if conflicts:
            status = "conflict"
            trust_label = "Widerspruch"
            recommendation = "Manuelle Prüfung erforderlich; Videoinhalt gegenüber einem möglicherweise falschen Dateinamen bevorzugen."
        elif final_confidence >= 0.90 and len(confirmed) >= 3:
            status = "confirmed"
            trust_label = "sehr hoch"
            recommendation = "Identität kann als bestätigt übernommen werden; Änderungen weiterhin nur nach Vorschau und Bestätigung."
        elif final_confidence >= 0.78 and len(confirmed) >= 2:
            status = "probable"
            trust_label = "hoch"
            recommendation = "Erkennung ist wahrscheinlich richtig; vor automatischer Umbenennung einmal prüfen."
        elif final_confidence >= 0.62:
            status = "review_recommended"
            trust_label = "mittel"
            recommendation = "Weitere Online-, OCR-, Untertitel- oder Fingerprint-Beweise sammeln."
        else:
            status = "insufficient"
            trust_label = "niedrig"
            recommendation = "Keine automatische Identitätsentscheidung treffen."

        explanation = self._build_explanation(title, confirmed, weak, conflicts, status)

        return {
            "schema_version": 3,
            "status": status,
            "title_candidate": title or None,
            "media_type": identification.get("media_type"),
            "season": identification.get("season"),
            "episodes": identification.get("episodes") or [],
            "confidence": round(final_confidence, 4),
            "confidence_percent": round(final_confidence * 100, 1),
            "trust_label": trust_label,
            "support_strength": round(support_strength, 4),
            "independent_confirmations": independence,
            "confirmed_evidence": confirmed,
            "weak_or_neutral_evidence": weak,
            "all_evidence": evidence,
            "conflicts": conflicts,
            "recommendation": recommendation,
            "explanation": explanation,
            "automatic_change_allowed": False,
            "review_required": status != "confirmed",
        }

    def _combine(self, evidence: list[dict[str, Any]]) -> tuple[float, float, int]:
        positive = [item for item in evidence if item["supports"]]
        if not positive:
            return 0.0, 0.0, 0
        product = 1.0
        for item in positive:
            product *= 1.0 - item["weighted_score"]
        combined = 1.0 - product
        independence = len({item["source"] for item in positive if item["weighted_score"] >= 0.20})
        independence_bonus = min(0.12, max(0, independence - 1) * 0.03)
        strength = sum(item["weighted_score"] for item in positive) / max(1, len(positive))
        return self._clamp(combined + independence_bonus), strength, independence

    def _item(self, source: str, label: str, value: str, confidence: float, supports: bool, detail: str) -> dict[str, Any]:
        confidence = self._clamp(confidence)
        weight = self.SOURCE_WEIGHTS.get(source, 0.30)
        weighted = confidence * weight if supports else 0.0
        return {
            "source": source,
            "label": label,
            "value": value,
            "confidence": round(confidence, 4),
            "confidence_percent": round(confidence * 100, 1),
            "weight": weight,
            "supports": supports,
            "weighted_score": round(weighted, 4),
            "detail": detail,
        }

    @staticmethod
    def _identity_label(identity: Any) -> str:
        if not isinstance(identity, dict):
            return str(identity or "Treffer")
        title = str(identity.get("title") or "Treffer")
        season = identity.get("season")
        episode = identity.get("episode")
        suffix = ""
        if season is not None and episode is not None:
            suffix = f" S{int(season):02d}E{int(episode):02d}"
        return f"{title}{suffix}"

    @staticmethod
    def _build_explanation(title: str, confirmed: list[dict[str, Any]], weak: list[dict[str, Any]], conflicts: list[dict[str, Any]], status: str) -> dict[str, Any]:
        reasons = [f"{item['label']} bestätigt: {item['value']}." for item in confirmed]
        limitations = [item.get("detail") for item in weak if item.get("detail")]
        if conflicts:
            conclusion = "Die Quellen widersprechen sich; eine manuelle Prüfung ist notwendig."
        elif status == "confirmed":
            conclusion = f"Mehrere unabhängige Quellen bestätigen {title or 'den erkannten Titel'} eindeutig."
        elif status == "probable":
            conclusion = f"Mehrere Hinweise sprechen für {title or 'den erkannten Titel'}, ohne einen eindeutigen Referenztreffer."
        elif status == "review_recommended":
            conclusion = "Die vorhandenen Hinweise reichen noch nicht für eine sichere Übernahme."
        else:
            conclusion = "Die Identität konnte nicht zuverlässig bestimmt werden."
        return {
            "why": reasons,
            "limitations": limitations,
            "conflicts": [f"{c['left_source']} ({c['left_value']}) widerspricht {c['right_source']} ({c['right_value']})." for c in conflicts],
            "conclusion": conclusion,
            "human_review": status != "confirmed",
        }

    @staticmethod
    def _conflict(field: str, left_source: str, left_value: str, right_source: str, right_value: str, severity: str) -> dict[str, Any]:
        return {
            "field": field,
            "left_source": left_source,
            "left_value": left_value,
            "right_source": right_source,
            "right_value": right_value,
            "severity": severity,
        }

    @classmethod
    def _best_token_match(cls, target: str, values: list[str]) -> tuple[float, str | None]:
        if not target:
            return 0.0, None
        best_score = 0.0
        best_value: str | None = None
        for value in values:
            normalized = cls._normalize(value)
            if not normalized:
                continue
            score = cls._similarity(target, normalized)
            if target in normalized or normalized in target:
                score = max(score, 0.82)
            if score > best_score:
                best_score, best_value = score, value
        return best_score, best_value

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio()

    @staticmethod
    def _normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
        return " ".join(value.split())

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
