from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

_TARGET_UID_NAMES = {
    "TrackUID",
    "EditionUID",
    "ChapterUID",
    "AttachmentUID",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _direct_child(element, name: str):
    for child in list(element):
        if child.tag == name:
            return child
    return None


def _target_type_value(tag: ET.Element) -> str:
    targets = _direct_child(tag, "Targets")

    if targets is None:
        return ""

    node = _direct_child(
        targets,
        "TargetTypeValue",
    )

    if node is not None and _clean(node.text):
        return _clean(node.text)

    # Matroska definiert 50 als Standardwert f?r
    # TargetTypeValue. MKVToolNix darf diesen
    # Standardwert beim Schreiben weglassen.
    #
    # <Targets>
    #   <TargetType>EPISODE</TargetType>
    # </Targets>
    #
    # ist daher semantisch TargetTypeValue=50.
    return "50"


def _has_specific_uid(tag: ET.Element) -> bool:
    targets = _direct_child(tag, "Targets")

    if targets is None:
        return False

    return any(
        child.tag in _TARGET_UID_NAMES
        and _clean(child.text)
        for child in list(targets)
    )


def _find_or_create_scope(
    root: ET.Element,
    *,
    target_value: int | None,
    target_type: str = "",
) -> ET.Element:
    expected = (
        str(target_value)
        if target_value is not None
        else ""
    )

    for tag in root.findall("Tag"):
        if _has_specific_uid(tag):
            continue

        if _target_type_value(tag) == expected:
            return tag

    tag = ET.SubElement(root, "Tag")
    targets = ET.SubElement(tag, "Targets")

    if target_value is not None:
        value_node = ET.SubElement(
            targets,
            "TargetTypeValue",
        )
        value_node.text = str(target_value)

        if target_type:
            type_node = ET.SubElement(
                targets,
                "TargetType",
            )
            type_node.text = target_type

    return tag


def _find_simple(
    tag: ET.Element,
    name: str,
) -> ET.Element | None:
    wanted = name.upper()

    for simple in tag.findall("Simple"):
        name_node = simple.find("Name")

        if (
            name_node is not None
            and _clean(name_node.text).upper()
            == wanted
        ):
            return simple

    return None


def _set_simple(
    tag: ET.Element,
    name: str,
    value: Any,
) -> None:
    value = _clean(value)

    if not value:
        return

    simple = _find_simple(tag, name)

    if simple is None:
        simple = ET.SubElement(tag, "Simple")

        name_node = ET.SubElement(
            simple,
            "Name",
        )
        name_node.text = name.upper()

        string_node = ET.SubElement(
            simple,
            "String",
        )
    else:
        string_node = simple.find("String")

        if string_node is None:
            string_node = ET.SubElement(
                simple,
                "String",
            )

    string_node.text = value


def _released(metadata: dict) -> str:
    return _clean(
        metadata.get("published_at")
        or metadata.get("year")
    )


def merge_mediahub_matroska_tags(
    xml_text: str,
    metadata: dict,
) -> str:
    source = str(xml_text or "").strip()

    if source:
        try:
            root = ET.fromstring(source)
        except ET.ParseError as error:
            raise ValueError(
                f"Ung?ltige Matroska-Tag-XML: {error}"
            ) from error
    else:
        root = ET.Element("Tags")

    if root.tag != "Tags":
        raise ValueError(
            "Matroska-Tag-XML besitzt kein Tags-Wurzelelement."
        )

    media_type = _clean(
        metadata.get("media_type")
    ).lower()

    description = _clean(
        metadata.get("description")
    )
    released = _released(metadata)

    if media_type == "series":
        series = _clean(metadata.get("series"))
        season = _clean(metadata.get("season"))
        episode = _clean(metadata.get("episode"))
        episode_title = _clean(
            metadata.get("episode_title")
            or metadata.get("title")
        )

        if series:
            collection = _find_or_create_scope(
                root,
                target_value=70,
                target_type="COLLECTION",
            )
            _set_simple(
                collection,
                "TITLE",
                series,
            )

        if season or released:
            season_tag = _find_or_create_scope(
                root,
                target_value=60,
                target_type="SEASON",
            )
            _set_simple(
                season_tag,
                "PART_NUMBER",
                season,
            )
            _set_simple(
                season_tag,
                "DATE_RELEASED",
                released,
            )

        if (
            episode
            or episode_title
            or description
        ):
            episode_tag = _find_or_create_scope(
                root,
                target_value=50,
                target_type="EPISODE",
            )

            _set_simple(
                episode_tag,
                "TITLE",
                episode_title,
            )
            _set_simple(
                episode_tag,
                "PART_NUMBER",
                episode,
            )
            _set_simple(
                episode_tag,
                "DESCRIPTION",
                description,
            )

    elif media_type == "movie":
        movie = _find_or_create_scope(
            root,
            target_value=50,
            target_type="MOVIE",
        )

        _set_simple(
            movie,
            "DESCRIPTION",
            description,
        )
        _set_simple(
            movie,
            "DATE_RELEASED",
            released,
        )

    else:
        # Allgemeines Video:
        # keine k?nstliche MOVIE-/EPISODE-Klassifikation.
        generic = _find_or_create_scope(
            root,
            target_value=None,
        )

        _set_simple(
            generic,
            "DESCRIPTION",
            description,
        )
        _set_simple(
            generic,
            "DATE_RELEASED",
            released,
        )

    if hasattr(ET, "indent"):
        ET.indent(root, space="  ")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(
            root,
            encoding="unicode",
        )
        + "\n"
    )


def read_mediahub_matroska_tags(
    xml_text: str,
) -> dict:
    source = str(xml_text or "").strip()

    if not source:
        return {}

    try:
        root = ET.fromstring(source)
    except ET.ParseError:
        return {}

    if root.tag != "Tags":
        return {}

    result = {}
    parsed_tags = []

    def simple_values(tag):
        values = {}

        for simple in tag.findall("Simple"):
            name = _clean(
                simple.findtext("Name")
            ).upper()

            value = _clean(
                simple.findtext("String")
            )

            if name and value:
                values[name] = value

        return values

    # Erst alle globalen Tags erfassen.
    for tag in root.findall("Tag"):
        if _has_specific_uid(tag):
            continue

        targets = _direct_child(tag, "Targets")
        target_type = ""

        if targets is not None:
            target_type = _clean(
                targets.findtext("TargetType")
            ).upper()

        parsed_tags.append(
            {
                "target_value": _target_type_value(tag),
                "target_type": target_type,
                "values": simple_values(tag),
            }
        )

    # Serienkontext zuerst bestimmen. MKVToolNix kann
    # Standardwerte/-bezeichnungen beim Schreiben weglassen.
    series_context = any(
        entry["target_value"] in {"60", "70"}
        or entry["target_type"] in {
            "SEASON",
            "COLLECTION",
        }
        for entry in parsed_tags
    )

    for entry in parsed_tags:
        target_value = entry["target_value"]
        target_type = entry["target_type"]
        values = entry["values"]

        if (
            target_value == "70"
            or target_type == "COLLECTION"
        ):
            if values.get("TITLE"):
                result["series"] = values["TITLE"]

            continue

        if (
            target_value == "60"
            or target_type == "SEASON"
        ):
            if values.get("PART_NUMBER"):
                try:
                    result["season"] = int(
                        values["PART_NUMBER"]
                    )
                except ValueError:
                    pass

            released = values.get("DATE_RELEASED")

            if released and released[:4].isdigit():
                result["year"] = int(
                    released[:4]
                )

            continue

        if target_value != "50" and target_type not in {
            "EPISODE",
            "MOVIE",
        }:
            continue

        # Bei TargetTypeValue=50 darf MKVToolNix den
        # Standardwert und teilweise die Bezeichnung
        # weglassen. In einer Collection-/Season-Struktur
        # ist Ebene 50 daher die Episode.
        is_episode = (
            target_type == "EPISODE"
            or (
                not target_type
                and (
                    series_context
                    or bool(values.get("PART_NUMBER"))
                )
            )
        )

        is_movie = target_type == "MOVIE"

        if is_episode:
            result["media_type"] = "series"

            if values.get("TITLE"):
                result["episode_title"] = (
                    values["TITLE"]
                )

            if values.get("PART_NUMBER"):
                try:
                    result["episode"] = int(
                        values["PART_NUMBER"]
                    )
                except ValueError:
                    pass

        elif is_movie:
            result["media_type"] = "movie"

        if values.get("DESCRIPTION"):
            result["description"] = (
                values["DESCRIPTION"]
            )

        released = values.get("DATE_RELEASED")

        if released and released[:4].isdigit():
            result["year"] = int(
                released[:4]
            )

    # Wenn Collection/Season vorhanden ist, ist die Datei
    # auch dann eine Serie, wenn der Episode-Tag keinerlei
    # explizite Typbezeichnung mehr enth?lt.
    if series_context:
        result["media_type"] = "series"

    return result

