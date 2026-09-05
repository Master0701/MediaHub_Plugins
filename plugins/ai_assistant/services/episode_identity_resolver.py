from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any


class EpisodeIdentityResolver:
    """Bestimmt Serienepisoden aus Inhalts- und Provider-Evidenz.

    Der Resolver darf keine Episode allein aus einem schwachen Worttreffer
    übernehmen. Beziehungen zwischen mehreren Handlungskonzepten werden
    deutlich stärker gewichtet als isolierte Begriffe.
    """

    STOPWORDS = {
        "aber", "alle", "alles", "als", "also", "am",
        "an", "auch", "auf", "aus", "bei", "bin",
        "bis", "da", "das", "dass", "dem", "den",
        "der", "des", "die", "dies", "diese", "dieser",
        "doch", "du", "durch", "ein", "eine", "einem",
        "einen", "einer", "eines", "er", "es", "für",
        "hat", "haben", "hier", "ich", "ihm", "ihn",
        "im", "in", "ist", "ja", "man", "mit",
        "nach", "nicht", "noch", "nur", "oder", "sich",
        "sie", "sind", "so", "um", "und", "uns",
        "von", "vor", "war", "was", "wenn", "wer",
        "wie", "wird", "wir", "wo", "zu", "zum",
        "zur",
    }

    CONCEPTS = {
        "military": {
            "marine", "marines", "sergeant", "navy",
            "soldat", "soldatin", "militär", "militaer",
            "lieutenant", "commander", "officer",
        },
        "intruder": {
            "einbrecher", "einbruch", "eingebrochen",
            "einbricht", "eindringling", "unbekannter",
            "unbekannte",
        },
        "shooting": {
            "erschossen", "erschießt", "erschiesst",
            "erschießen", "erschiessen", "schießt",
            "schiesst", "schießen", "schiessen",
            "schuss", "schüsse", "schuesse",
        },
        "house": {
            "haus", "wohnung", "wohnhaus", "zuhause",
            "zimmer", "garage",
        },
        "death": {
            "tot", "toter", "tote", "toten", "leiche",
            "getötet", "getoetet", "ermordet",
        },
        "killer": {
            "killer", "auftragskiller", "mörder", "moerder",
        },
        "fingerprints": {
            "fingerabdruck", "fingerabdrücke",
            "fingerabdruecke", "finger",
        },
        "explosion": {
            "explosion", "explodiert", "explodieren",
            "bombe", "sprengstoff",
        },
        "kidnapping": {
            "entführt", "entfuehrt", "entführung",
            "entfuehrung", "geisel", "gefangen",
        },
        "fire": {
            "feuer", "brand", "brennt", "verbrannt",
        },
        "vehicle": {
            "auto", "wagen", "fahrzeug", "boot", "schiff",
            "flugzeug",
        },
        "hospital": {
            "krankenhaus", "hospital", "arzt", "ärztin",
            "aerztin",
        },
    }

    def __init__(self, source_manager) -> None:
        self.source_manager = source_manager

    @staticmethod
    def _normalize(value: Any) -> str:
        text = unicodedata.normalize(
            "NFKD",
            str(value or ""),
        )

        text = "".join(
            char
            for char in text
            if not unicodedata.combining(char)
        )

        return text.casefold()

    @classmethod
    def _tokens(cls, value: Any) -> list[str]:
        return [
            token
            for token in re.findall(
                r"[a-z0-9äöüß'-]{2,}",
                cls._normalize(value),
            )
            if token not in cls.STOPWORDS
        ]

    @classmethod
    def _concept_hits(
        cls,
        value: Any,
    ) -> set[str]:
        token_set = set(
            cls._tokens(value)
        )

        result: set[str] = set()

        for concept, vocabulary in cls.CONCEPTS.items():
            normalized_vocabulary = {
                cls._normalize(item)
                for item in vocabulary
            }

            if token_set & normalized_vocabulary:
                result.add(concept)

        return result

    @classmethod
    def _sentences(
        cls,
        value: Any,
    ) -> list[str]:
        return [
            part.strip()
            for part in re.split(
                r"(?<=[.!?])\s+|\n+",
                str(value or ""),
            )
            if part.strip()
        ]

    @classmethod
    def _relationships(
        cls,
        value: Any,
    ) -> Counter:
        result: Counter = Counter()

        for sentence in cls._sentences(value):
            concepts = sorted(
                cls._concept_hits(sentence)
            )

            for index, left in enumerate(concepts):
                for right in concepts[index + 1:]:
                    result[(left, right)] += 1

        return result

    @staticmethod
    def _series_title(
        analysis: dict[str, Any],
    ) -> str:
        online_best = (
            (
                (analysis.get("online") or {})
                .get("ranking")
                or {}
            )
            .get("best_match")
            or {}
        )

        semantic_best = (
            (
                analysis.get("semantic_identity")
                or {}
            )
            .get("best_candidate")
            or {}
        )

        source_reasoning = (
            (
                (
                    analysis.get("source_plan")
                    or {}
                )
                .get("query")
                or {}
            )
            .get("query_reasoning")
            or {}
        )

        for value in (
            online_best.get("original_title"),
            online_best.get("title"),
            semantic_best.get("original_title"),
            semantic_best.get("title"),
            source_reasoning.get("primary_title"),
        ):
            text = str(value or "").strip()
            if text:
                return text

        return ""

    @staticmethod
    def _series_is_confirmed(
        analysis: dict[str, Any],
    ) -> bool:
        decision_type = str(
            (
                analysis.get("decision")
                or {}
            ).get("media_type")
            or ""
        ).strip().casefold()

        if decision_type == "series":
            return True

        online_best = (
            (
                (analysis.get("online") or {})
                .get("ranking")
                or {}
            )
            .get("best_match")
            or {}
        )

        semantic_best = (
            (
                analysis.get("semantic_identity")
                or {}
            )
            .get("best_candidate")
            or {}
        )

        return (
            str(
                online_best.get("media_type")
                or ""
            ).strip().casefold()
            == "series"
            or str(
                semantic_best.get("media_type")
                or ""
            ).strip().casefold()
            == "series"
        )

    def resolve(
        self,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._series_is_confirmed(analysis):
            return {
                "schema_version": 1,
                "status": "not_applicable",
                "reason": "Medientyp ist keine bestätigte Serie.",
                "decision_authority": False,
            }

        speech = (
            analysis.get(
                "speech_identity_evidence"
            )
            or {}
        )

        transcript = str(
            speech.get("transcript")
            or ""
        ).strip()

        if not transcript:
            return {
                "schema_version": 1,
                "status": "insufficient",
                "reason": "Kein Speech-Transkript für Episodenabgleich vorhanden.",
                "decision_authority": False,
            }

        title = self._series_title(
            analysis
        )

        if not title:
            return {
                "schema_version": 1,
                "status": "insufficient",
                "reason": "Keine bestätigte Serienidentität vorhanden.",
                "decision_authority": False,
            }

        candidates = (
            self.source_manager
            .list_episode_candidates(
                {
                    "title": title,
                    "media_type": "series",
                    "max_candidates": 1000,
                }
            )
        )

        if not candidates:
            return {
                "schema_version": 1,
                "status": "insufficient",
                "series_title": title,
                "reason": "Keine Episodenkandidaten verfügbar.",
                "decision_authority": False,
            }

        speech_concepts = (
            self._concept_hits(
                transcript
            )
        )
        speech_relationships = (
            self._relationships(
                transcript
            )
        )
        speech_tokens = set(
            self._tokens(
                transcript
            )
        )

        ranked: list[
            dict[str, Any]
        ] = []

        for candidate in candidates:
            candidate_text = " ".join(
                [
                    str(
                        candidate.get(
                            "episode_title"
                        )
                        or ""
                    ),
                    str(
                        candidate.get(
                            "overview"
                        )
                        or ""
                    ),
                ]
            )

            candidate_concepts = (
                self._concept_hits(
                    candidate_text
                )
            )

            shared_concepts = (
                speech_concepts
                & candidate_concepts
            )

            candidate_relationships = set(
                self._relationships(
                    candidate_text
                )
            )

            matched_relationships = [
                pair
                for pair
                in speech_relationships
                if pair in candidate_relationships
            ]

            shared_tokens = (
                speech_tokens
                & set(
                    self._tokens(
                        candidate_text
                    )
                )
            )

            concept_score = float(
                len(shared_concepts)
            )

            relationship_score = sum(
                2.5
                * speech_relationships[pair]
                for pair
                in matched_relationships
            )

            lexical_score = (
                min(
                    len(shared_tokens),
                    10,
                )
                * 0.08
            )

            # Ein zusätzlicher Synergiebonus wird nur vergeben,
            # wenn mehrere inhaltlich zusammengehörige Konzepte
            # gleichzeitig übereinstimmen.
            synergy_score = 0.0

            if len(shared_concepts) >= 4:
                synergy_score += 4.0
            elif len(shared_concepts) >= 3:
                synergy_score += 2.0

            if (
                len(matched_relationships)
                >= 3
            ):
                synergy_score += 3.0
            elif (
                len(matched_relationships)
                >= 2
            ):
                synergy_score += 1.5

            score = (
                concept_score
                + relationship_score
                + lexical_score
                + synergy_score
            )

            ranked.append(
                {
                    "score": round(
                        score,
                        4,
                    ),
                    "candidate":
                        dict(candidate),
                    "shared_concepts":
                        sorted(
                            shared_concepts
                        ),
                    "matched_relationships":
                        [
                            list(pair)
                            for pair
                            in matched_relationships
                        ],
                    "shared_tokens":
                        sorted(
                            shared_tokens
                        )[:20],
                    "score_parts": {
                        "concept":
                            round(
                                concept_score,
                                4,
                            ),
                        "relationship":
                            round(
                                relationship_score,
                                4,
                            ),
                        "lexical":
                            round(
                                lexical_score,
                                4,
                            ),
                        "synergy":
                            round(
                                synergy_score,
                                4,
                            ),
                    },
                }
            )

        ranked.sort(
            key=lambda item: (
                float(
                    item.get("score")
                    or 0.0
                ),
                len(
                    item.get(
                        "shared_concepts"
                    )
                    or []
                ),
                len(
                    item.get(
                        "matched_relationships"
                    )
                    or []
                ),
            ),
            reverse=True,
        )

        best = (
            ranked[0]
            if ranked
            else None
        )
        second = (
            ranked[1]
            if len(ranked) > 1
            else None
        )

        if best is None:
            return {
                "schema_version": 1,
                "status": "insufficient",
                "series_title": title,
                "reason": "Kein Episodenkandidat konnte bewertet werden.",
                "decision_authority": False,
            }

        best_score = float(
            best.get("score")
            or 0.0
        )
        second_score = float(
            (
                second
                or {}
            ).get("score")
            or 0.0
        )

        score_gap = (
            best_score
            - second_score
        )

        ratio = (
            best_score
            / second_score
            if second_score > 0
            else float("inf")
        )

        concept_count = len(
            best.get(
                "shared_concepts"
            )
            or []
        )
        relationship_count = len(
            best.get(
                "matched_relationships"
            )
            or []
        )

        # Harte Sicherheitsgrenze:
        # Eine Episode gilt nur dann als bestätigt,
        # wenn mehrere Handlungskonzepte UND mindestens
        # eine Beziehung übereinstimmen und der Abstand
        # zum Zweitplatzierten eindeutig ist.
        confirmed = (
            best_score >= 8.0
            and concept_count >= 3
            and relationship_count >= 1
            and score_gap >= 3.0
            and ratio >= 1.5
        )

        probable = (
            not confirmed
            and best_score >= 5.0
            and concept_count >= 2
            and relationship_count >= 1
            and score_gap >= 1.5
            and ratio >= 1.2
        )

        status = (
            "confirmed"
            if confirmed
            else (
                "probable"
                if probable
                else "insufficient"
            )
        )

        candidate = dict(
            best.get("candidate")
            or {}
        )

        confidence = 0.0

        if confirmed:
            confidence = min(
                0.99,
                0.82
                + min(
                    score_gap / 50.0,
                    0.12,
                )
                + min(
                    relationship_count
                    * 0.015,
                    0.05,
                ),
            )
        elif probable:
            confidence = min(
                0.84,
                0.60
                + min(
                    score_gap / 30.0,
                    0.12,
                ),
            )

        return {
            "schema_version": 1,
            "status": status,
            "series_title": title,
            "season": (
                candidate.get("season")
                if confirmed
                else None
            ),
            "episode": (
                candidate.get("episode")
                if confirmed
                else None
            ),
            "episodes": (
                [
                    candidate.get(
                        "episode"
                    )
                ]
                if (
                    confirmed
                    and candidate.get(
                        "episode"
                    )
                    is not None
                )
                else []
            ),
            "episode_title": (
                candidate.get(
                    "episode_title"
                )
                if confirmed
                else None
            ),
            "confidence": round(
                confidence,
                4,
            ),
            "confidence_percent":
                round(
                    confidence * 100,
                    1,
                ),
            "score": round(
                best_score,
                4,
            ),
            "runner_up_score":
                round(
                    second_score,
                    4,
                ),
            "score_gap": round(
                score_gap,
                4,
            ),
            "score_ratio": (
                round(
                    ratio,
                    4,
                )
                if ratio
                != float("inf")
                else None
            ),
            "shared_concepts":
                best.get(
                    "shared_concepts"
                )
                or [],
            "matched_relationships":
                best.get(
                    "matched_relationships"
                )
                or [],
            "shared_tokens":
                best.get(
                    "shared_tokens"
                )
                or [],
            "score_parts":
                best.get(
                    "score_parts"
                )
                or {},
            "provider":
                candidate.get(
                    "provider"
                ),
            "provider_name":
                candidate.get(
                    "provider_name"
                ),
            "episode_external_id":
                candidate.get(
                    "episode_external_id"
                ),
            "overview":
                candidate.get(
                    "overview"
                ),
            "candidate_count":
                len(ranked),
            "top_candidates":
                ranked[:10],
            "decision_authority":
                confirmed,
            "reason": (
                "Episodenidentität durch mehrere "
                "zusammenhängende In-Video-/Speech-"
                "Handlungshinweise bestätigt."
                if confirmed
                else (
                    "Episodenkandidat ist wahrscheinlich, "
                    "aber noch nicht stark genug für eine "
                    "automatische Übernahme."
                    if probable
                    else
                    "Episodenbeweise reichen noch nicht "
                    "für eine sichere Zuordnung."
                )
            ),
        }
