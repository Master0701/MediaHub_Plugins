import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.narrative_extractor import NarrativeExtractor


def test_extracts_conflict_and_resolution():
    text = (
        "David greift Atlantis an und bedroht Arthur. "
        "Später besiegt Arthur Kordax und rettet Mera."
    )
    result = NarrativeExtractor.extract(
        text=text,
        primary_title="Aquaman: Lost Kingdom",
    )

    assert result["summary"]["conflict_count"] >= 1
    assert result["summary"]["resolution_count"] >= 1
    assert result["automatic_import"] is False


def test_extracts_character_growth():
    text = (
        "Orm arbeitet mit Arthur zusammen und hilft ihm. "
        "Später übernimmt Orm Verantwortung und rettet Atlantis."
    )
    result = NarrativeExtractor.extract(
        text=text,
        primary_title="Aquaman: Lost Kingdom",
    )

    assert result["summary"]["character_growth_count"] >= 2


def test_extracts_repeated_motif():
    text = (
        "Arthur schützt seinen Sohn und seine Familie. "
        "Sein Halbbruder hilft der Familie später erneut."
    )
    result = NarrativeExtractor.extract(
        text=text,
        primary_title="Aquaman: Lost Kingdom",
    )

    assert result["summary"]["motif_count"] >= 1
