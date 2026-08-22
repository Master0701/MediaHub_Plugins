import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.filename_identifier import FilenameIdentifier


def test_windows_copy_suffix_is_removed():
    identifier = FilenameIdentifier()

    cases = (
        ("Chappie - Kopie.mp4", "Chappie"),
        ("Chappie - Copy.mp4", "Chappie"),
        ("Chappie - Kopie (2).mp4", "Chappie"),
        ("Chappie - Copy (2).mp4", "Chappie"),
    )

    for filename, expected in cases:
        result = identifier.identify(filename)
        assert result["title_candidate"] == expected


def test_real_title_containing_kopie_is_preserved():
    identifier = FilenameIdentifier()

    result = identifier.identify(
        "Die Kopie.mp4"
    )

    assert result["title_candidate"] == "Die Kopie"


def test_real_title_containing_copy_is_preserved():
    identifier = FilenameIdentifier()

    result = identifier.identify(
        "The Copy.mp4"
    )

    assert result["title_candidate"] == "The Copy"
