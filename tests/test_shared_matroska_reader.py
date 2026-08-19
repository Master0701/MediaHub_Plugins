from mediahub_metadata_core import (
    read_mediahub_matroska_tags,
)


def test_read_series_tags():
    xml = """<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TargetTypeValue>70</TargetTypeValue>
      <TargetType>COLLECTION</TargetType>
    </Targets>
    <Simple>
      <Name>TITLE</Name>
      <String>Testserie</String>
    </Simple>
  </Tag>

  <Tag>
    <Targets>
      <TargetTypeValue>60</TargetTypeValue>
      <TargetType>SEASON</TargetType>
    </Targets>
    <Simple>
      <Name>PART_NUMBER</Name>
      <String>2</String>
    </Simple>
    <Simple>
      <Name>DATE_RELEASED</Name>
      <String>2026</String>
    </Simple>
  </Tag>

  <Tag>
    <Targets>
      <TargetType>EPISODE</TargetType>
    </Targets>
    <Simple>
      <Name>TITLE</Name>
      <String>Der Test</String>
    </Simple>
    <Simple>
      <Name>PART_NUMBER</Name>
      <String>7</String>
    </Simple>
    <Simple>
      <Name>DESCRIPTION</Name>
      <String>Eine Testfolge</String>
    </Simple>
  </Tag>
</Tags>
"""

    result = read_mediahub_matroska_tags(xml)

    assert result["media_type"] == "series"
    assert result["series"] == "Testserie"
    assert result["season"] == 2
    assert result["episode"] == 7
    assert result["episode_title"] == "Der Test"
    assert result["description"] == "Eine Testfolge"
    assert result["year"] == 2026


def test_read_movie_tags():
    xml = """<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TargetType> MOVIE </TargetType>
    </Targets>
    <Simple>
      <Name>DESCRIPTION</Name>
      <String>Filmtext</String>
    </Simple>
    <Simple>
      <Name>DATE_RELEASED</Name>
      <String>1999</String>
    </Simple>
  </Tag>
</Tags>
"""

    result = read_mediahub_matroska_tags(xml)

    assert result["media_type"] == "movie"
    assert result["description"] == "Filmtext"
    assert result["year"] == 1999


def test_track_tags_are_ignored():
    xml = """<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TrackUID>123</TrackUID>
    </Targets>
    <Simple>
      <Name>TITLE</Name>
      <String>Nicht übernehmen</String>
    </Simple>
  </Tag>
</Tags>
"""

    result = read_mediahub_matroska_tags(xml)

    assert result == {}
