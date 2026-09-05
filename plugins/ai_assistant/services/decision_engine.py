from __future__ import annotations

from services.input_quality import evaluate_text

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
        "episode_identity": 0.86,
        "technical": 0.30,
        "scene": 0.24,
        "audio": 0.20,
    }

    def evaluate_online_identity(
        self,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Bewertet, ob der beste Online-Treffer die lokale Identität trägt.

        Diese Funktion ist die gemeinsame Wahrheit für DecisionEngine und
        Supervisor. Ein Ranking-Label allein reicht ausdrücklich nicht.
        """
        identification = analysis.get("identification") or {}
        online = analysis.get("online") or {}
        ranking = online.get("ranking") or {}
        best = ranking.get("best_match") or {}

        title = str(
            identification.get("title_candidate") or ""
        ).strip()
        normalized_title = self._normalize(title)

        if not best:
            return {
                "supported": False,
                "confidence": 0.0,
                "reason": "Kein Online-Treffer vorhanden.",
                "kind": "none",
            }

        candidate = str(best.get("title") or "").strip()
        candidate_conf = self._clamp(
            float(best.get("score") or 0.0)
        )

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

        title_words = normalized_title.split()

        strong_alias_prefix_match = bool(
            len(title_words) >= 3
            and any(
                alias != normalized_title
                and alias.startswith(
                    normalized_title + " "
                )
                for alias in normalized_aliases
            )
        )

        ranking_decision = str(
            ranking.get("decision") or ""
        ).strip().lower()

        penalties = {
            str(item)
            for item in (best.get("penalties") or [])
        }

        evidence_count = int(
            best.get("evidence_count") or 0
        )

        blocking_penalties = {
            "weak_single_word_variant",
            "insufficient_combined_evidence",
        }

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
                        exact_title_providers.add(
                            provider_id
                        )
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

        normal_confirmation = (
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

        alias_confirmation = (
            (
                exact_alias_match
                or strong_alias_prefix_match
            )
            and candidate_conf >= 0.35
        )

        supported = (
            normal_confirmation
            or multi_provider_confirmation
            or alias_confirmation
        )

        if alias_confirmation:
            kind = "alias"
        elif multi_provider_confirmation:
            kind = "multi_provider"
        elif normal_confirmation:
            kind = "normal"
        else:
            kind = "unsupported"

        return {
            "supported": supported,
            "confidence": (
                candidate_conf
                if supported
                else 0.0
            ),
            "candidate_confidence": candidate_conf,
            "similarity": similarity,
            "evidence_count": evidence_count,
            "ranking_decision": ranking_decision,
            "penalties": sorted(penalties),
            "exact_title_providers": sorted(
                exact_title_providers
            ),
            "exact_alias_match": exact_alias_match,
            "strong_alias_prefix_match":
                strong_alias_prefix_match,
            "kind": kind,
        }

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        online = analysis.get("online") or {}
        in_video = analysis.get("in_video") or {}
        agents = in_video.get("agents") or {}

        filename_title = str(
            identification.get(
                "title_candidate"
            )
            or ""
        ).strip()

        local_confidence = self._clamp(
            float(
                identification.get(
                    "confidence"
                )
                or 0.0
            )
        )

        filename_quality = evaluate_text(
            filename_title,
            source="filename",
        )

        filename_identity_usable = bool(
            filename_title
            and filename_quality.accepted
            and not self._looks_like_compact_code(
                filename_title
            )
        )

        source_plan = (
            analysis.get("source_plan")
            or {}
        )
        source_query = (
            source_plan.get("query")
            or {}
        )
        query_reasoning = (
            source_query.get("query_reasoning")
            or {}
        )

        recovered_title = str(
            query_reasoning.get(
                "primary_title"
            )
            or ""
        ).strip()

        semantic = (
            analysis.get("semantic_identity")
            or {}
        )
        semantic_best = (
            semantic.get("best_candidate")
            or {}
        )

        semantic_title = str(
            semantic_best.get("title")
            or ""
        ).strip()

        online_title_best = (
            (online.get("ranking") or {})
            .get("best_match")
            or {}
        )

        online_title = str(
            online_title_best.get(
                "original_title"
            )
            or online_title_best.get(
                "title"
            )
            or ""
        ).strip()

        title = (
            filename_title
            if filename_identity_usable
            else (
                recovered_title
                or online_title
                or semantic_title
                or filename_title
            )
        )

        normalized_title = self._normalize(
            title
        )

        known_media_types = {
            "movie",
            "series",
        }

        local_media_type = str(
            identification.get("media_type")
            or ""
        ).strip().lower()

        online_best = (
            (online.get("ranking") or {})
            .get("best_match")
            or {}
        )
        online_media_type = str(
            online_best.get("media_type")
            or online_best.get("type")
            or ""
        ).strip().lower()

        semantic_media_type = str(
            semantic_best.get("media_type")
            or ""
        ).strip().lower()

        if local_media_type in known_media_types:
            effective_media_type = local_media_type
        elif online_media_type in known_media_types:
            effective_media_type = online_media_type
        elif semantic_media_type in known_media_types:
            effective_media_type = semantic_media_type
        else:
            effective_media_type = (
                local_media_type
                or "unknown"
            )

        evidence: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []

        if filename_title:
            evidence.append(
                self._item(
                    source="filename",
                    label="Dateiname",
                    value=filename_title,
                    confidence=(
                        local_confidence
                        if filename_identity_usable
                        else 0.0
                    ),
                    supports=filename_identity_usable,
                    detail=(
                        "Titel- und Episodenmuster aus "
                        "Datei- oder Ordnernamen."
                        if filename_identity_usable
                        else
                        "Dateiname wurde durch das "
                        "Identitäts-Quality-Gate als "
                        "unzuverlässig eingestuft und "
                        "nicht als Medienidentität verwendet."
                    ),
                )
            )

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

            # Offizielle Alternativtitel können einen bekannten Haupttitel
            # als Zusatz enthalten, z. B.:
            #
            #   Live Die Repeat
            #   Live Die Repeat: Edge of Tomorrow
            #
            # Ein Teiltreffer gilt nur dann als starker Alias-Hinweis, wenn
            # der lokale Titel aus mindestens drei Wörtern besteht und als
            # vollständiger Wort-Präfix eines offiziellen Alias vorkommt.
            # Dadurch werden unsichere Einwort-/Kurztreffer vermieden.
            title_words = normalized_title.split()

            strong_alias_prefix_match = bool(
                len(title_words) >= 3
                and any(
                    alias != normalized_title
                    and alias.startswith(normalized_title + " ")
                    for alias in normalized_aliases
                )
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

            alias_confirmation = (
                (
                    exact_alias_match
                    or strong_alias_prefix_match
                )
                and candidate_conf >= 0.35
            )

            identity_supported = (
                normal_online_confirmation
                or multi_provider_confirmation
                or alias_confirmation
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
                    if (
                        exact_alias_match
                        or strong_alias_prefix_match
                    ):
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

            # Ein bereits bestätigter offizieller Alias-/Präfix-Treffer
            # darf für die Evidenzbewertung die echte Provider-Confidence
            # verwenden. Der Ranking-Score kann zuvor durch Alias- oder
            # Ähnlichkeitsstrafen reduziert worden sein und bildet dann
            # nicht mehr die Stärke des offiziellen Provider-Belegs ab.
            if alias_confirmation:
                alias_provider_confidences: list[float] = []

                for provider_result in provider_results:
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

                        try:
                            provider_confidence = float(
                                match.get("provider_confidence")
                                or 0.0
                            )
                        except (TypeError, ValueError):
                            provider_confidence = 0.0

                        if provider_confidence > 0:
                            alias_provider_confidences.append(
                                self._clamp(provider_confidence)
                            )

                if alias_provider_confidences:
                    online_evidence_confidence = max(
                        online_evidence_confidence,
                        max(alias_provider_confidences),
                    )

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
            if (
                filename_identity_usable
                and filename_title
                and similarity < 0.35
                and candidate_conf >= 0.65
            ):
                conflicts.append(
                    self._conflict(
                        "title",
                        "Dateiname",
                        filename_title,
                        "Online",
                        candidate,
                        "hoch",
                    )
                )

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

        episode_identity = (
            analysis.get(
                "episode_identity"
            )
            or {}
        )

        episode_status = str(
            episode_identity.get(
                "status"
            )
            or ""
        ).strip().casefold()

        episode_authority = bool(
            episode_identity.get(
                "decision_authority"
            )
        )

        if (
            episode_status == "confirmed"
            and episode_authority
        ):
            episode_season = (
                episode_identity.get(
                    "season"
                )
            )
            episode_number = (
                episode_identity.get(
                    "episode"
                )
            )
            episode_title = str(
                episode_identity.get(
                    "episode_title"
                )
                or ""
            ).strip()

            episode_value = title

            if (
                episode_season is not None
                and episode_number is not None
            ):
                episode_value += (
                    f" S{int(episode_season):02d}"
                    f"E{int(episode_number):02d}"
                )

            if episode_title:
                episode_value += (
                    f" – {episode_title}"
                )

            episode_confidence = self._clamp(
                float(
                    episode_identity.get(
                        "confidence"
                    )
                    or 0.0
                )
            )

            concepts = [
                str(value)
                for value in (
                    episode_identity.get(
                        "shared_concepts"
                    )
                    or []
                )
                if str(value).strip()
            ]

            relationships = [
                "+".join(
                    str(part)
                    for part in pair
                )
                for pair in (
                    episode_identity.get(
                        "matched_relationships"
                    )
                    or []
                )
                if isinstance(
                    pair,
                    (list, tuple),
                )
            ]

            detail_parts = [
                (
                    "Konkrete Serienepisode wurde durch "
                    "In-Video-/Speech-Handlungsevidenz "
                    "gegen Provider-Episodendaten bestätigt."
                )
            ]

            if concepts:
                detail_parts.append(
                    "Konzepte: "
                    + ", ".join(concepts)
                    + "."
                )

            if relationships:
                detail_parts.append(
                    "Beziehungen: "
                    + ", ".join(
                        relationships
                    )
                    + "."
                )

            score_gap = (
                episode_identity.get(
                    "score_gap"
                )
            )

            if score_gap is not None:
                detail_parts.append(
                    "Abstand zum zweitbesten "
                    f"Episodenkandidaten: "
                    f"{float(score_gap):.2f}."
                )

            evidence.append(
                self._item(
                    source="episode_identity",
                    label="In-Video-Episode",
                    value=episode_value,
                    confidence=episode_confidence,
                    supports=True,
                    detail=" ".join(
                        detail_parts
                    ),
                )
            )

        decision_confidence, support_strength, independence = self._combine(evidence)
        contradiction_penalty = min(0.35, sum(0.16 if c["severity"] == "hoch" else 0.08 for c in conflicts))
        final_confidence = self._clamp(decision_confidence - contradiction_penalty)

        confirmed = [item for item in evidence if item["supports"] and item["weighted_score"] >= 0.22]
        weak = [item for item in evidence if not item["supports"] or item["weighted_score"] < 0.22]

        confirmed_sources = {
            str(
                item.get("source")
                or ""
            ).strip()
            for item in confirmed
        }

        strong_episode_confirmation = (
            episode_status == "confirmed"
            and episode_authority
            and "episode_identity"
            in confirmed_sources
        )

        strong_online_confirmation = (
            "online"
            in confirmed_sources
        )

        series_episode_confirmation = (
            final_confidence >= 0.93
            and len(confirmed) >= 2
            and strong_episode_confirmation
            and strong_online_confirmation
        )

        if conflicts:
            status = "conflict"
            trust_label = "Widerspruch"
            recommendation = "Manuelle Prüfung erforderlich; Videoinhalt gegenüber einem möglicherweise falschen Dateinamen bevorzugen."
        elif (
            final_confidence >= 0.90
            and len(confirmed) >= 3
        ) or series_episode_confirmation:
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

        episode_identity = (
            analysis.get(
                "episode_identity"
            )
            or {}
        )

        episode_confirmed = (
            str(
                episode_identity.get(
                    "status"
                )
                or ""
            ).strip().casefold()
            == "confirmed"
            and bool(
                episode_identity.get(
                    "decision_authority"
                )
            )
        )

        if episode_confirmed:
            effective_season = (
                episode_identity.get(
                    "season"
                )
            )
            effective_episodes = list(
                episode_identity.get(
                    "episodes"
                )
                or (
                    [
                        episode_identity.get(
                            "episode"
                        )
                    ]
                    if episode_identity.get(
                        "episode"
                    )
                    is not None
                    else []
                )
            )
        else:
            effective_season = (
                identification.get(
                    "season"
                )
            )
            effective_episodes = list(
                identification.get(
                    "episodes"
                )
                or []
            )

        explanation = self._build_explanation(title, confirmed, weak, conflicts, status)

        return {
            "schema_version": 3,
            "status": status,
            "title_candidate": title or None,
            "media_type": effective_media_type,
            "season": effective_season,
            "episodes": effective_episodes,
            "episode_identity": (
                dict(episode_identity)
                if episode_identity
                else None
            ),
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
    def _looks_like_compact_code(
        value: str,
    ) -> bool:
        """Erkennt zufällige kompakte Buchstaben-/Zahlencodes.

        Beispiele wie 6n76g68r dürfen nicht als belastbare
        Medienidentität oder Dateinamentitel verwendet werden.
        """

        text = re.sub(
            r"[^A-Za-z0-9]",
            "",
            str(value or ""),
        )

        if len(text) < 6:
            return False

        letters = sum(
            char.isalpha()
            for char in text
        )

        digits = sum(
            char.isdigit()
            for char in text
        )

        if not letters or not digits:
            return False

        letter_ratio = (
            letters / len(text)
        )
        digit_ratio = (
            digits / len(text)
        )

        transitions = sum(
            left.isdigit()
            != right.isdigit()
            for left, right in zip(
                text,
                text[1:],
            )
        )

        return (
            letter_ratio < 0.60
            and digit_ratio >= 0.30
            and transitions >= 3
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
