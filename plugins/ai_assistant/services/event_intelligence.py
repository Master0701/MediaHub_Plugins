from __future__ import annotations

import re
import uuid
from typing import Any

from services.battle_parser import BattleParser
from services.plot_cleaner import PlotCleaner
from services.event_character_identity_resolver import EventCharacterIdentityResolver


class EventIntelligence:
    """Erzeugt bestätigungspflichtige Ereignisknoten aus Handlungstext."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str) -> str:
        normalized = " ".join(str(title or "").casefold().split())
        return f"{kind}:{normalized}"

    @staticmethod
    def _event_key(event_type: str, sequence: int) -> str:
        return f"event:{event_type}:{sequence:04d}"

    @classmethod
    def _clean_name(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"^(?:der|die|das|ein|eine|einen|einer|seinen|seine|ihren|ihre)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.split(
            r"\s+(?:alias|auch bekannt als)\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return text.strip(" ,.;:")

    @classmethod
    def _clean_event_person(cls, value: str) -> str:
        text = cls._clean_name(value)
        text = re.split(
            r"\s+(?:aus|vom|von|mit|bei|gegen|um|nach|in|auf|"
            r"bevor|während|als|wo|der|die|das)\b",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        text = re.split(
            r"(?<=[.!?])\s+",
            text,
            maxsplit=1,
        )[0]
        return text.strip(" ,.;:")

    @classmethod
    def _extract_plot_text(cls, text: str) -> str:
        source = str(text or "")
        if not source:
            return ""

        # Wikipedia-Seiten enthalten "Handlung" und "Produktion" zuerst
        # im Inhaltsverzeichnis. Bevorzugt werden deshalb die echten
        # Abschnittsüberschriften mit Bearbeiten-Markierung.
        explicit_patterns = (
            (
                r"\bHandlung\b\s*"
                r"\[\s*Bearbeiten\s*\|\s*Quelltext bearbeiten\s*\]"
                r"\s*(?P<plot>.+?)"
                r"(?=\bProduktion\b\s*"
                r"\[\s*Bearbeiten\s*\|\s*Quelltext bearbeiten\s*\]|\Z)"
            ),
            (
                r"\bHandlung\b\s*"
                r"\[\s*Bearbeiten[^\]]*\]"
                r"\s*(?P<plot>.+?)"
                r"(?=\bProduktion\b\s*\[\s*Bearbeiten[^\]]*\]|\Z)"
            ),
        )

        for pattern in explicit_patterns:
            match = re.search(
                pattern,
                source,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group("plot").strip()

        # Fallback für andere Quellen ohne Wikipedia-Markierungen:
        # Das letzte plausible Handlung-Vorkommen vor Produktion wird
        # verwendet, nicht blind der erste Treffer aus dem Inhaltsverzeichnis.
        starts = list(
            re.finditer(
                r"\bHandlung\b(?:\s*\[[^\]]*\])?",
                source,
                flags=re.IGNORECASE,
            )
        )
        ends = list(
            re.finditer(
                r"\bProduktion\b(?:\s*\[[^\]]*\])?",
                source,
                flags=re.IGNORECASE,
            )
        )

        candidates: list[str] = []
        for start in starts:
            end = next(
                (
                    item
                    for item in ends
                    if item.start() > start.end()
                ),
                None,
            )
            if end is None:
                continue

            candidate = source[start.end():end.start()].strip()
            if candidate:
                candidates.append(candidate)

        if candidates:
            return max(candidates, key=len)

        return source

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        compact = cls._norm(text)
        if not compact:
            return []

        protected = compact
        abbreviations = (
            "Jr.",
            "Sr.",
            "Dr.",
            "Prof.",
            "Mr.",
            "Mrs.",
            "Ms.",
        )
        placeholders: dict[str, str] = {}

        for index, abbreviation in enumerate(abbreviations):
            placeholder = f"__ABBR_{index}__"
            placeholders[placeholder] = abbreviation
            protected = re.sub(
                re.escape(abbreviation),
                placeholder,
                protected,
                flags=re.IGNORECASE,
            )

        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+", protected)
            if item.strip()
        ]

        restored: list[str] = []
        for sentence in sentences:
            for placeholder, abbreviation in placeholders.items():
                sentence = sentence.replace(placeholder, abbreviation)
            restored.append(sentence)

        return restored

    @classmethod
    def _valid_character_name(cls, value: str) -> bool:
        name = cls._clean_name(value)
        if not name:
            return False
        forbidden = {
            "er", "sie", "ihn", "ihm", "ihr", "ist", "hat",
            "dass", "und", "als", "sein halbbruder",
        }
        if name.casefold() in forbidden:
            return False
        if any(token in name.casefold() for token in (
            " nachdem ", " bevor ", " während ", " dass ",
            " zu befreien", " kommt mit ", " ergebnis",
        )):
            return False
        return len(name.split()) <= 5

    def analyze(self, *, text: str, source: dict[str, Any]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        warnings: list[str] = []
        node_index: dict[str, dict[str, Any]] = {}
        event_count = 0

        def add_node(
            node_type: str,
            title: str,
            confidence: float,
            reason: str,
            metadata: dict[str, Any] | None = None,
            key_override: str | None = None,
        ) -> dict[str, Any] | None:
            title = self._clean_name(title)
            if not title:
                return None

            key = key_override or self._key(node_type, title)
            existing = node_index.get(key)
            if existing is not None:
                existing["metadata"].update(dict(metadata or {}))
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(confidence),
                )
                return existing

            item = {
                "id": uuid.uuid4().hex,
                "key": key,
                "node_type": node_type,
                "title": title,
                "metadata": dict(metadata or {}),
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            }
            node_index[key] = item
            nodes.append(item)
            return item

        def add_edge(
            edge_type: str,
            source_node: dict[str, Any] | None,
            target_node: dict[str, Any] | None,
            confidence: float,
            reason: str,
            sentence: str,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if source_node is None or target_node is None:
                return

            duplicate = any(
                edge["edge_type"] == edge_type
                and edge["source_node_key"] == source_node["key"]
                and edge["target_node_key"] == target_node["key"]
                for edge in edges
            )
            if duplicate:
                return

            evidence_id = uuid.uuid4().hex
            evidence.append(
                {
                    "id": evidence_id,
                    "text": sentence,
                    "edge_type": edge_type,
                    "source_id": source.get("id"),
                }
            )
            edges.append(
                {
                    "id": uuid.uuid4().hex,
                    "edge_type": edge_type,
                    "source_node_key": source_node["key"],
                    "target_node_key": target_node["key"],
                    "confidence": round(float(confidence), 4),
                    "reason": reason,
                    "metadata": dict(metadata or {}),
                    "evidence_id": evidence_id,
                    "source_id": source.get("id"),
                    "status": "proposed",
                    "requires_confirmation": True,
                }
            )

        def create_event(
            event_type: str,
            sentence: str,
            confidence: float,
            metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            nonlocal event_count
            event_count += 1
            return add_node(
                "event",
                f"{event_type.replace('_', ' ').title()} #{event_count}",
                confidence,
                f"Ereignis aus Handlungstext: {event_type}.",
                {
                    "event_type": event_type,
                    "sequence": event_count,
                    "evidence_text": sentence,
                    **dict(metadata or {}),
                },
                key_override=self._event_key(event_type, event_count),
            )

        extracted_plot_text = self._extract_plot_text(text)
        plot_text = PlotCleaner.clean(extracted_plot_text)
        sentences = self._sentences(plot_text)

        person = (
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*"
            r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*){0,3}?"
        )
        place = (
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*"
            r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*){0,3}?"
        )
        artifact = (
            r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9.'-]*"
            r"(?:\s+[A-Za-zÄÖÜäöüß0-9.'-]+){0,4}?"
        )

        for sentence in sentences:
            # Arthur besiegte Black Manta in Necrus mit dem schwarzen Dreizack.
            victory = re.search(
                rf"\b(?P<actor>{person})\s+besiegt(?:e)?\s+"
                rf"(?P<opponent>{person})"
                rf"(?=\s+in\s+|\s+mit\s+|[.!?]|$)"
                rf"(?:\s+in\s+(?P<location>{place})"
                rf"(?=\s+mit\s+|[.!?]|$))?"
                rf"(?:\s+mit\s+(?:dem|der|einem|einer)\s+"
                rf"(?P<artifact>{artifact})(?=[.!?]|$))?",
                sentence,
                flags=re.IGNORECASE,
            )
            if victory:
                actor_name = victory.group("actor")
                opponent_name = victory.group("opponent")
                if self._valid_character_name(actor_name) and self._valid_character_name(opponent_name):
                    actor = add_node("character", actor_name, 0.88, "Gewinner.")
                    opponent = add_node("character", opponent_name, 0.88, "Verlierer.")
                    event = create_event("victory", victory.group(0), 0.88)
                    add_edge("participates_in", actor, event, 0.88, "Teilnehmer.", victory.group(0), {"role": "winner"})
                    add_edge("participates_in", opponent, event, 0.88, "Teilnehmer.", victory.group(0), {"role": "loser"})
                    add_edge("winner", event, actor, 0.90, "Expliziter Gewinner.", victory.group(0))
                    add_edge("loser", event, opponent, 0.90, "Expliziter Verlierer.", victory.group(0))
                    if victory.group("location"):
                        location = add_node("location", victory.group("location"), 0.82, "Ereignisort.")
                        add_edge("occurs_at", event, location, 0.84, "Ereignisort.", victory.group(0))
                    if victory.group("artifact"):
                        item = add_node("artifact", victory.group("artifact"), 0.82, "Verwendetes Artefakt.")
                        add_edge("uses", event, item, 0.84, "Verwendetes Artefakt.", victory.group(0))

            for battle_result in BattleParser.parse(sentence):
                actor_name = battle_result["actor"]
                opponent_name = battle_result["opponent"]

                if (
                    self._valid_character_name(actor_name)
                    and self._valid_character_name(opponent_name)
                ):
                    actor = add_node(
                        "character",
                        actor_name,
                        0.88,
                        "Kampfteilnehmer.",
                    )
                    opponent = add_node(
                        "character",
                        opponent_name,
                        0.88,
                        "Kampfteilnehmer.",
                    )
                    event = create_event(
                        "battle",
                        battle_result["evidence"],
                        0.88,
                        {
                            "parser": battle_result["parser"],
                            **(
                                {"context": battle_result["context"]}
                                if battle_result.get("context")
                                else {}
                            ),
                        },
                    )
                    add_edge(
                        "participates_in",
                        actor,
                        event,
                        0.88,
                        "Kampfteilnehmer.",
                        battle_result["evidence"],
                        {"role": "attacker"},
                    )
                    add_edge(
                        "participates_in",
                        opponent,
                        event,
                        0.88,
                        "Kampfteilnehmer.",
                        battle_result["evidence"],
                        {"role": "opponent"},
                    )

                    if battle_result.get("location"):
                        location = add_node(
                            "location",
                            battle_result["location"],
                            0.84,
                            "Kampfort.",
                        )
                        add_edge(
                            "occurs_at",
                            event,
                            location,
                            0.86,
                            "Kampfort.",
                            battle_result["evidence"],
                        )

            # Subjekt zuerst:
            # "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis."
            rescue = re.search(
                rf"\b(?P<rescuer>{person})\s+"
                rf"(?:rettet|rettete|befreit|befreite)\s+"
                rf"(?:seinen|ihren|den|die)\s+"
                rf"(?:(?P<kinship>"
                rf"Halbbruder|Halbschwester|Bruder|Schwester"
                rf")\s+)?"
                rf"(?P<rescued>{person})"
                rf"(?=\s+aus\b|\s+in\b|\s+nach\b|,|[.!?]|$)",
                sentence,
                flags=re.IGNORECASE,
            )

            # Verb zuerst nach Nebensatz oder Einleitung:
            # "..., befreit Arthur seinen Halbbruder Orm ..."
            if not rescue:
                rescue = re.search(
                    rf"(?:^|,\s*)"
                    rf"(?:rettet|rettete|befreit|befreite)\s+"
                    rf"(?P<rescuer>{person})\s+"
                    rf"(?:seinen|ihren|den|die)\s+"
                    rf"(?:(?P<kinship>"
                    rf"Halbbruder|Halbschwester|Bruder|Schwester"
                    rf")\s+)?"
                    rf"(?P<rescued>{person})"
                    rf"(?=\s+aus\b|\s+in\b|\s+nach\b|,|[.!?]|$)",
                    sentence,
                    flags=re.IGNORECASE,
                )

            # Allgemeiner Rettungsfall ohne Verwandtschaftsbezeichnung.
            if not rescue:
                rescue = re.search(
                    rf"\b(?P<rescuer>{person})\s+"
                    rf"(?:rettet|rettete|befreit|befreite)\s+"
                    rf"(?P<rescued>{person})"
                    rf"(?=\s+aus\b|\s+in\b|\s+nach\b|,|[.!?]|$)",
                    sentence,
                    flags=re.IGNORECASE,
                )

            if rescue:
                rescuer_name = self._clean_event_person(
                    rescue.group("rescuer")
                )
                rescued_name = self._clean_event_person(
                    rescue.group("rescued")
                )

                if (
                    self._valid_character_name(rescuer_name)
                    and self._valid_character_name(rescued_name)
                ):
                    rescuer = add_node(
                        "character",
                        rescuer_name,
                        0.86,
                        "Retter.",
                    )
                    rescued = add_node(
                        "character",
                        rescued_name,
                        0.86,
                        "Gerettete Figur.",
                    )

                    kinship = rescue.groupdict().get("kinship")

                    event = create_event(
                        "rescue",
                        rescue.group(0),
                        0.86,
                        {"kinship": kinship} if kinship else None,
                    )
                    add_edge(
                        "participant",
                        event,
                        rescuer,
                        0.86,
                        "Retter.",
                        rescue.group(0),
                        {"role": "rescuer"},
                    )
                    add_edge(
                        "participant",
                        event,
                        rescued,
                        0.86,
                        "Gerettete Figur.",
                        rescue.group(0),
                        {
                            "role": "rescued",
                            **(
                                {"kinship": kinship}
                                if kinship
                                else {}
                            ),
                        },
                    )

            # "... dass David Arthur Jr. entführt hat."
            kidnapping = re.search(
                rf"\b(?:dass\s+)?(?P<kidnapper>{person})\s+"
                rf"(?P<victim>{person})\s+entführt\s+hat\b",
                sentence,
                flags=re.IGNORECASE,
            )
            if not kidnapping:
                kidnapping = re.search(
                    rf"\b(?P<kidnapper>{person})\s+entführt(?:e)?\s+"
                    rf"(?P<victim>{person})(?=,|[.!?]|$)",
                    sentence,
                    flags=re.IGNORECASE,
                )
            if kidnapping:
                kidnapper_name = re.sub(r"^dass\s+", "", kidnapping.group("kidnapper"), flags=re.IGNORECASE)
                victim_name = kidnapping.group("victim")
                if self._valid_character_name(kidnapper_name) and self._valid_character_name(victim_name):
                    kidnapper = add_node("character", kidnapper_name, 0.90, "Entführer.")
                    victim = add_node("character", victim_name, 0.90, "Entführte Figur.")
                    event = create_event("kidnapping", kidnapping.group(0), 0.90)
                    add_edge("participant", event, kidnapper, 0.90, "Entführer.", kidnapping.group(0), {"role": "kidnapper"})
                    add_edge("participant", event, victim, 0.90, "Opfer.", kidnapping.group(0), {"role": "victim"})

            # Named subject only; pronouns like "Er findet" are deliberately skipped.
            discovery = re.search(
                rf"\b(?P<finder>{person})\s+(?:findet|fand)\s+"
                rf"(?:einen|eine|ein|den|die|das)\s+"
                rf"(?P<object>{artifact})(?=,|[.!?]|$)",
                sentence,
                flags=re.IGNORECASE,
            )
            if discovery and self._valid_character_name(discovery.group("finder")):
                finder = add_node("character", discovery.group("finder"), 0.80, "Finder.")
                item = add_node("artifact", discovery.group("object"), 0.80, "Gefundenes Artefakt.")
                event = create_event("discovery", discovery.group(0), 0.80)
                add_edge("participant", event, finder, 0.80, "Finder.", discovery.group(0), {"role": "finder"})
                add_edge("object", event, item, 0.82, "Gefundenes Objekt.", discovery.group(0))

            creation = re.search(
                rf"\b(?P<object>{artifact})\s+"
                rf"(?:wurde|war)\s+von\s+(?P<creator>{person})\s+"
                rf"(?:erschaffen|geschaffen|gebaut)",
                sentence,
                flags=re.IGNORECASE,
            )
            if creation and self._valid_character_name(creation.group("creator")):
                item = add_node("artifact", creation.group("object"), 0.86, "Erschaffenes Artefakt.")
                creator = add_node("character", creation.group("creator"), 0.86, "Schöpfer.")
                event = create_event("creation", creation.group(0), 0.86)
                add_edge("participant", event, creator, 0.86, "Schöpfer.", creation.group(0), {"role": "creator"})
                add_edge("object", event, item, 0.86, "Erschaffenes Objekt.", creation.group(0))

        if event_count == 0:
            warnings.append("Keine sicheren Ereignisse erkannt.")

        result = {
            "schema_version": 1,
            "strategy": "event_intelligence_v386",
            "event_count": event_count,
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }

        return EventCharacterIdentityResolver.resolve_result(
            text=text,
            result=result,
        )
