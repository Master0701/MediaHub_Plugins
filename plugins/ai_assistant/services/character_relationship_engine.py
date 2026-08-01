from __future__ import annotations

import re
from typing import Any


class CharacterRelationshipEngine:
    """Extrahiert belastbare Figurenbeziehungen aus Handlungstexten."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _key(cls, title: str) -> str:
        return f"character:{cls._norm(title).casefold()}"

    @classmethod
    def _node(
        cls,
        title: str,
        *,
        confidence: float,
        reason: str,
        source_id: Any,
    ) -> dict[str, Any]:
        name = cls._norm(title).strip(" ,.;:")
        return {
            "key": cls._key(name),
            "node_type": "character",
            "title": name,
            "confidence": confidence,
            "metadata": {
                "relationship_engine": "character_relationship_engine_v413",
            },
            "reason": reason,
            "source_id": source_id,
            "requires_confirmation": True,
        }

    @classmethod
    def _edge(
        cls,
        edge_type: str,
        source_title: str,
        target_title: str,
        *,
        confidence: float,
        reason: str,
        evidence: str,
        source_id: Any,
    ) -> dict[str, Any]:
        return {
            "edge_type": edge_type,
            "source_node_key": cls._key(source_title),
            "target_node_key": cls._key(target_title),
            "confidence": confidence,
            "metadata": {
                "relationship_engine": "character_relationship_engine_v413",
                "evidence": cls._norm(evidence),
            },
            "reason": reason,
            "source_id": source_id,
            "requires_confirmation": True,
        }

    @classmethod
    def _clean_name(cls, value: str) -> str:
        name = cls._norm(value)
        name = re.sub(
            r"^(?:der|die|das|sein|seine|seinen|ihr|ihre|ihren)\s+",
            "",
            name,
            flags=re.IGNORECASE,
        )
        return name.strip(" ,.;:")

    @classmethod
    def _add_relation(
        cls,
        *,
        nodes: dict[str, dict[str, Any]],
        edges: dict[tuple[str, str, str], dict[str, Any]],
        edge_type: str,
        source_title: str,
        target_title: str,
        confidence: float,
        reason: str,
        evidence: str,
        source_id: Any,
        reciprocal_type: str | None = None,
    ) -> None:
        source_title = cls._clean_name(source_title)
        target_title = cls._clean_name(target_title)

        if not source_title or not target_title:
            return
        if source_title.casefold() == target_title.casefold():
            return

        for title in (source_title, target_title):
            key = cls._key(title)
            nodes.setdefault(
                key,
                cls._node(
                    title,
                    confidence=confidence,
                    reason=reason,
                    source_id=source_id,
                ),
            )

        edge = cls._edge(
            edge_type,
            source_title,
            target_title,
            confidence=confidence,
            reason=reason,
            evidence=evidence,
            source_id=source_id,
        )
        edges[
            (
                edge_type,
                edge["source_node_key"],
                edge["target_node_key"],
            )
        ] = edge

        if reciprocal_type:
            reciprocal = cls._edge(
                reciprocal_type,
                target_title,
                source_title,
                confidence=confidence,
                reason=reason,
                evidence=evidence,
                source_id=source_id,
            )
            edges[
                (
                    reciprocal_type,
                    reciprocal["source_node_key"],
                    reciprocal["target_node_key"],
                )
            ] = reciprocal

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        content = cls._norm(text)
        return [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+", content)
            if item.strip()
        ]

    @classmethod
    def _relationship_name(cls, value: str) -> str:
        name = cls._clean_name(value)
        name = re.sub(
            r"^(?:König|Königin|Prinz|Prinzessin)\s+",
            lambda match: match.group(0),
            name,
            flags=re.IGNORECASE,
        )
        return name.strip(" ,.;:")

    @classmethod
    def _build_identity_map(
        cls,
        identity_map: dict[str, str] | None,
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in dict(identity_map or {}).items():
            short = cls._norm(key).casefold()
            canonical = cls._norm(value)
            if short and canonical:
                result[short] = canonical
        return result

    @classmethod
    def _resolve_identity(
        cls,
        value: str,
        identity_map: dict[str, str],
    ) -> str:
        name = cls._relationship_name(value)
        return identity_map.get(name.casefold(), name)

    @classmethod
    def _subject_before_half_sibling(
        cls,
        sentence: str,
        relation_start: int,
    ) -> str | None:
        """Bestimmt das Subjekt im letzten Satzteil vor der Beziehung.

        Beispiele:
        - Arthur befreit seinen Halbbruder Orm
        - Um herauszufinden, ..., befreit Arthur seinen Halbbruder Orm

        Nach dem letzten Komma wird der unmittelbar vor der
        Verwandtschaftsphrase liegende Satzteil ausgewertet.
        """
        prefix = sentence[:relation_start].strip()
        if not prefix:
            return None

        clause = re.split(r"[,;:]\s*", prefix)[-1].strip()
        if not clause:
            return None

        blocked = {
            "um",
            "als",
            "wenn",
            "weil",
            "obwohl",
            "während",
            "nachdem",
            "bevor",
            "unterdessen",
            "daraufhin",
            "später",
        }

        tokens = re.findall(
            r"[A-ZÄÖÜ][\wÄÖÜäöüß.'’\-]+|"
            r"[a-zäöüß][\wÄÖÜäöüß.'’\-]+|"
            r"Jr\.?|II|III|IV",
            clause,
        )
        if not tokens:
            return None

        # In der Verb-Erstform steht das Subjekt direkt nach dem Verb:
        # "befreit Arthur"
        if (
            len(tokens) >= 2
            and tokens[0][:1].islower()
            and tokens[1][:1].isupper()
        ):
            candidate = tokens[1]

            # Optionaler zweiter Namensbestandteil.
            if (
                len(tokens) >= 3
                and tokens[2][:1].isupper()
                and tokens[2].casefold() not in blocked
            ):
                candidate = f"{candidate} {tokens[2]}"

            candidate = cls._relationship_name(candidate)
            if candidate.casefold() not in blocked:
                return candidate

        # In der normalen Hauptsatzform steht das Subjekt am Anfang:
        # "Arthur befreit"
        if tokens[0][:1].isupper():
            candidate = tokens[0]

            if (
                len(tokens) >= 2
                and tokens[1][:1].isupper()
                and (
                    len(tokens) == 2
                    or tokens[2][:1].islower()
                )
            ):
                candidate = f"{candidate} {tokens[1]}"

            candidate = cls._relationship_name(candidate)
            if candidate.casefold() not in blocked:
                return candidate

        return None

    @classmethod
    def analyze(
        cls,
        *,
        text: str,
        source: dict[str, Any] | None = None,
        identity_map: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        identities = cls._build_identity_map(identity_map)

        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        evidence: list[dict[str, Any]] = []

        name = (
            r"[A-ZÄÖÜ][\wÄÖÜäöüß.'’\-]+"
            r"(?:\s+(?:[A-ZÄÖÜ][\wÄÖÜäöüß.'’\-]+|Jr\.?|II|III|IV))?"
        )

        for sentence in cls._sentences(text):
            shared_subject: str | None = None

            # Deutsche Nebensatz-/Verb-Erstform:
            # "... heiratete Arthur Curry Mera und bekam einen Sohn, Arthur Jr."
            marriage_after_verb = re.search(
                rf"\bheiratete\s+(?P<a>{name})\s+(?P<b>{name})"
                rf"(?=\s+und\b|[,.;]|$)",
                sentence,
            )
            if marriage_after_verb:
                a = cls._resolve_identity(marriage_after_verb.group("a"), identities)
                b = cls._resolve_identity(marriage_after_verb.group("b"), identities)
                shared_subject = a

                cls._add_relation(
                    nodes=nodes,
                    edges=edges,
                    edge_type="spouse_of",
                    source_title=a,
                    target_title=b,
                    confidence=0.94,
                    reason="Explizite Heiratsbeziehung.",
                    evidence=marriage_after_verb.group(0),
                    source_id=source_id,
                    reciprocal_type="spouse_of",
                )
                evidence.append(
                    {
                        "edge_type": "spouse_of",
                        "source": a,
                        "target": b,
                        "sentence": cls._norm(marriage_after_verb.group(0)),
                        "confidence": 0.94,
                    }
                )

            # Normale Hauptsatzform:
            # "Arthur Curry heiratete Mera."
            for match in re.finditer(
                rf"\b(?P<a>{name})\s+heiratete\s+(?P<b>{name})"
                rf"(?=\s+und\b|[,.;]|$)",
                sentence,
            ):
                a = cls._resolve_identity(match.group("a"), identities)
                b = cls._resolve_identity(match.group("b"), identities)
                shared_subject = shared_subject or a

                cls._add_relation(
                    nodes=nodes,
                    edges=edges,
                    edge_type="spouse_of",
                    source_title=a,
                    target_title=b,
                    confidence=0.94,
                    reason="Explizite Heiratsbeziehung.",
                    evidence=match.group(0),
                    source_id=source_id,
                    reciprocal_type="spouse_of",
                )
                evidence.append(
                    {
                        "edge_type": "spouse_of",
                        "source": a,
                        "target": b,
                        "sentence": cls._norm(match.group(0)),
                        "confidence": 0.94,
                    }
                )

            # Explizites Subjekt bei Elternbeziehung.
            explicit_parent = re.search(
                rf"\b(?P<a>{name})\s+(?:bekam|hat)\s+"
                rf"(?:einen|eine)\s+(?:Sohn|Tochter)\s*,?\s*"
                rf"(?P<b>{name})",
                sentence,
            )
            if explicit_parent:
                parent = cls._resolve_identity(explicit_parent.group("a"), identities)
                child = cls._resolve_identity(explicit_parent.group("b"), identities)
                shared_subject = shared_subject or parent

                cls._add_relation(
                    nodes=nodes,
                    edges=edges,
                    edge_type="parent_of",
                    source_title=parent,
                    target_title=child,
                    confidence=0.92,
                    reason="Explizite Eltern-Kind-Beziehung.",
                    evidence=explicit_parent.group(0),
                    source_id=source_id,
                    reciprocal_type="child_of",
                )
                evidence.append(
                    {
                        "edge_type": "parent_of",
                        "source": parent,
                        "target": child,
                        "sentence": cls._norm(explicit_parent.group(0)),
                        "confidence": 0.92,
                    }
                )

            # Gemeinsames Subjekt:
            # "Arthur Curry heiratete Mera und bekam einen Sohn, Arthur Jr."
            if shared_subject:
                shared_child = re.search(
                    rf"\bund\s+bekam\s+(?:einen|eine)\s+"
                    rf"(?:Sohn|Tochter)\s*,?\s*(?P<b>{name})",
                    sentence,
                )
                if shared_child:
                    child = cls._resolve_identity(shared_child.group("b"), identities)

                    cls._add_relation(
                        nodes=nodes,
                        edges=edges,
                        edge_type="parent_of",
                        source_title=shared_subject,
                        target_title=child,
                        confidence=0.92,
                        reason=(
                            "Eltern-Kind-Beziehung mit gemeinsamem "
                            "Satzsubjekt."
                        ),
                        evidence=shared_child.group(0),
                        source_id=source_id,
                        reciprocal_type="child_of",
                    )
                    evidence.append(
                        {
                            "edge_type": "parent_of",
                            "source": shared_subject,
                            "target": child,
                            "sentence": cls._norm(shared_child.group(0)),
                            "confidence": 0.92,
                        }
                    )

            # Verb zwischen Subjekt und Verwandtschaftsbezeichnung.
            # Das Subjekt wird aus dem letzten Hauptsatzteil vor
            # "seinen Halbbruder" bzw. "seine Halbschwester" bestimmt.
            for label, reason in (
                ("seinen Halbbruder", "Explizite Halbbruder-Beziehung."),
                ("seine Halbschwester", "Explizite Halbschwester-Beziehung."),
            ):
                relation_match = re.search(
                    rf"\b{re.escape(label)}\s+(?P<b>{name})"
                    rf"(?=\s+(?:aus|von|mit|in|auf|bei|gegen|um|nach)\b|[,.;]|$)",
                    sentence,
                )
                if not relation_match:
                    continue

                subject = cls._subject_before_half_sibling(
                    sentence,
                    relation_match.start(),
                )
                if not subject:
                    continue

                a = cls._resolve_identity(subject, identities)
                b = cls._resolve_identity(
                    relation_match.group("b"),
                    identities,
                )

                cls._add_relation(
                    nodes=nodes,
                    edges=edges,
                    edge_type="half_sibling_of",
                    source_title=a,
                    target_title=b,
                    confidence=0.93,
                    reason=reason,
                    evidence=sentence[
                        max(0, relation_match.start() - 100):
                        relation_match.end()
                    ],
                    source_id=source_id,
                    reciprocal_type="half_sibling_of",
                )
                evidence.append(
                    {
                        "edge_type": "half_sibling_of",
                        "source": a,
                        "target": b,
                        "sentence": cls._norm(sentence),
                        "confidence": 0.93,
                    }
                )

            # Appositionen:
            # "Kordax, dem Bruder von König Atlan ..."
            for match in re.finditer(
                rf"\b(?P<a>{name})\s*,\s*(?:dem|der)\s+"
                rf"(?:Bruder|Schwester)\s+von\s+"
                rf"(?P<b>(?:König|Königin)\s+{name}|{name})"
                rf"(?=\s+(?:und|,|\.|$))",
                sentence,
            ):
                a = cls._resolve_identity(match.group("a"), identities)
                b = cls._resolve_identity(match.group("b"), identities)

                cls._add_relation(
                    nodes=nodes,
                    edges=edges,
                    edge_type="sibling_of",
                    source_title=a,
                    target_title=b,
                    confidence=0.91,
                    reason="Explizite Geschwisterbeziehung.",
                    evidence=match.group(0),
                    source_id=source_id,
                    reciprocal_type="sibling_of",
                )
                evidence.append(
                    {
                        "edge_type": "sibling_of",
                        "source": a,
                        "target": b,
                        "sentence": cls._norm(match.group(0)),
                        "confidence": 0.91,
                    }
                )

        return {
            "schema_version": 1,
            "strategy": "character_relationship_engine_v413",
            "relationship_count": len(edges),
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "evidence": evidence,
            "warnings": (
                []
                if edges
                else ["Keine sicheren Familienbeziehungen gefunden."]
            ),
            "automatic_import": False,
            "requires_confirmation": True,
        }
