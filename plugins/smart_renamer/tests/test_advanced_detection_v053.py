from pathlib import Path

from services.media_detection import MediaDetector
from services.media_scanner import MediaScanner
from services.rule_engine import RenameRuleEngine


def _detect(tmp_path: Path, name: str):
    path = tmp_path / name
    path.write_text("x", encoding="utf-8")
    return MediaDetector().detect(path)


def test_detects_multi_episode_sxxexx_dash(tmp_path: Path):
    result = _detect(tmp_path, "Serie S01E01-E02 Pilot.mkv")
    assert result.media_type == "series"
    assert result.season == "01"
    assert result.episode == "01"
    assert result.episode_end == "02"


def test_detects_multi_episode_sxxexxexx(tmp_path: Path):
    result = _detect(tmp_path, "Serie S01E01E02.mkv")
    assert result.episode == "01"
    assert result.episode_end == "02"


def test_detects_multi_episode_x_notation(tmp_path: Path):
    result = _detect(tmp_path, "Serie 2x03-04.mkv")
    assert result.season == "02"
    assert result.episode == "03"
    assert result.episode_end == "04"


def test_detects_episode_only(tmp_path: Path):
    result = _detect(tmp_path, "Meine Serie Folge 12.mkv")
    assert result.media_type == "series"
    assert result.episode == "12"
    assert result.confidence < 0.8


def test_detects_episode_short_ep(tmp_path: Path):
    result = _detect(tmp_path, "Meine Serie Ep05.mkv")
    assert result.media_type == "series"
    assert result.episode == "05"


def test_detects_special_by_season_zero(tmp_path: Path):
    result = _detect(tmp_path, "Serie S00E03 Weihnachtsspecial.mkv")
    assert result.is_special is True
    assert result.media_type == "series"


def test_detects_trailer_as_extra(tmp_path: Path):
    result = _detect(tmp_path, "Film 2024 Trailer.mkv")
    assert result.media_type == "extra"
    assert result.extra_type == "trailer"
    assert result.is_extra is True


def test_detects_bonus_as_extra(tmp_path: Path):
    result = _detect(tmp_path, "Film Bonus Interview.mkv")
    assert result.media_type == "extra"
    assert result.is_extra is True


def test_detects_deleted_scenes(tmp_path: Path):
    result = _detect(tmp_path, "Film Deleted Scenes.mkv")
    assert result.media_type == "extra"
    assert result.extra_type == "deleted_scene"


def test_detects_making_of(tmp_path: Path):
    result = _detect(tmp_path, "Film Making Of.mkv")
    assert result.media_type == "extra"
    assert result.extra_type == "making_of"


def test_detects_final_cut(tmp_path: Path):
    result = _detect(tmp_path, "Blade Runner 1982 Final Cut.mkv")
    assert result.media_type == "movie"
    assert result.edition == "Final Cut"


def test_detects_imax(tmp_path: Path):
    result = _detect(tmp_path, "Film 2023 IMAX.mkv")
    assert result.edition == "IMAX"


def test_detects_movie_part_number(tmp_path: Path):
    result = _detect(tmp_path, "Film Part 2 2024.mkv")
    assert result.media_type == "movie"
    assert result.part == "2"


def test_detects_cd_part(tmp_path: Path):
    result = _detect(tmp_path, "Film CD2 2024.mkv")
    assert result.part == "2"


def test_detects_trailing_roman_part(tmp_path: Path):
    result = _detect(tmp_path, "Rocky II 1979.mkv")
    assert result.media_type == "movie"
    assert result.part == "2"


def test_scanner_exposes_advanced_detection_fields(tmp_path: Path):
    path = tmp_path / "Serie S01E01-E02 Extended.mkv"
    path.write_text("x", encoding="utf-8")
    scanned, _ = MediaScanner().scan([{"path": str(path)}])
    item = scanned[0]
    assert item.episode_end == "02"
    assert item.edition == "Extended Cut"


def test_new_schema_placeholders_work():
    result = RenameRuleEngine().apply(
        "raw.mkv",
        [{
            "type": "schema",
            "template": "[titel] S[staffel]E[episode]-E[episode_bis] Part [part]",
        }],
        metadata={
            "titel": "Serie",
            "staffel": "01",
            "episode": "01",
            "episode_end": "02",
            "part": "2",
        },
    )
    assert result["proposed_name"] == "Serie S01E01-E02 Part 2.mkv"
