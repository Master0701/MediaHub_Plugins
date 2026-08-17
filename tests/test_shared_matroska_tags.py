import xml.etree.ElementTree as ET

from mediahub_metadata_core import (
    merge_mediahub_matroska_tags,
)


def _values(xml_text):
    root = ET.fromstring(xml_text)
    result = {}

    for tag in root.findall("Tag"):
        targets = tag.find("Targets")
        value = ""

        if targets is not None:
            node = targets.find(
                "TargetTypeValue"
            )
            if node is not None:
                value = node.text or ""

        fields = {}

        for simple in tag.findall("Simple"):
            name = simple.findtext("Name") or ""
            text = simple.findtext("String") or ""
            fields[name] = text

        result[value] = fields

    return result


def test_movie_metadata_uses_standard_tags():
    xml = merge_mediahub_matroska_tags(
        "",
        {
            "media_type": "movie",
            "description": "Ein Film",
            "year": 1999,
        },
    )

    values = _values(xml)

    assert values["50"]["DESCRIPTION"] == "Ein Film"
    assert values["50"]["DATE_RELEASED"] == "1999"


def test_series_uses_collection_season_episode():
    xml = merge_mediahub_matroska_tags(
        "",
        {
            "media_type": "series",
            "series": "Testserie",
            "season": 2,
            "episode": 7,
            "episode_title": "Der Test",
            "description": "Folgenbeschreibung",
            "year": 2026,
        },
    )

    values = _values(xml)

    assert values["70"]["TITLE"] == "Testserie"
    assert values["60"]["PART_NUMBER"] == "2"
    assert values["60"]["DATE_RELEASED"] == "2026"
    assert values["50"]["TITLE"] == "Der Test"
    assert values["50"]["PART_NUMBER"] == "7"
    assert (
        values["50"]["DESCRIPTION"]
        == "Folgenbeschreibung"
    )


def test_existing_track_tag_is_preserved():
    source = """<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TrackUID>12345</TrackUID>
    </Targets>
    <Simple>
      <Name>CUSTOM_TRACK_DATA</Name>
      <String>Nicht l?schen</String>
    </Simple>
  </Tag>
</Tags>
"""

    xml = merge_mediahub_matroska_tags(
        source,
        {
            "media_type": "movie",
            "description": "Neu",
            "year": 2001,
        },
    )

    assert "CUSTOM_TRACK_DATA" in xml
    assert "Nicht l?schen" in xml


def test_media_type_is_never_written_as_tag():
    xml = merge_mediahub_matroska_tags(
        "",
        {
            "media_type": "movie",
            "description": "Test",
        },
    )

    assert "MEDIA_TYPE" not in xml
    assert ">movie<" not in xml


def test_missing_target_type_value_means_default_50():
    source = """<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TargetType>EPISODE</TargetType>
    </Targets>
    <Simple>
      <Name>TITLE</Name>
      <String>Der Test</String>
    </Simple>
  </Tag>
</Tags>
"""

    xml = merge_mediahub_matroska_tags(
        source,
        {
            "media_type": "series",
            "episode": 7,
            "episode_title": "Der Test",
        },
    )

    root = ET.fromstring(xml)

    episode_tags = []

    for tag in root.findall("Tag"):
        targets = tag.find("Targets")

        if targets is None:
            continue

        target_type = (
            targets.findtext("TargetType")
            or ""
        )

        value = (
            targets.findtext("TargetTypeValue")
            or "50"
        )

        if target_type == "EPISODE" and value == "50":
            episode_tags.append(tag)

    assert len(episode_tags) == 1
