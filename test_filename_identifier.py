from pathlib import Path
import sys

PLUGIN = Path(__file__).parent / "plugins" / "ai_assistant"
sys.path.insert(0, str(PLUGIN))

from services.filename_identifier import FilenameIdentifier


def check(name: str, **expected):
    result = FilenameIdentifier().identify(name)
    for key, value in expected.items():
        assert result[key] == value, (name, key, result[key], value, result)


def main():
    check(
        "Star.Trek.Strange.New.Worlds.S02E03.1080p.WEB-DL.German.mkv",
        media_type="series", title_candidate="Star Trek Strange New Worlds",
        season=2, episode=3, episodes=[3],
    )
    check(
        "Doctor Who S04E12-E13 Journey's End 1080p.mkv",
        media_type="series", season=4, episode=12, episodes=[12, 13],
        is_multi_episode=True,
    )
    check(
        "NCIS Staffel 03 Folge 14 Deutsch.mkv",
        media_type="series", title_candidate="NCIS", season=3, episode=14,
    )
    check(
        "Stargate.SG-1.S00E05.Special.mkv",
        media_type="special", season=0, episode=5, is_special=True,
    )
    check(
        "Blade.Runner.1982.Final.Cut.Remastered.2160p.UHD.mkv",
        media_type="movie", title_candidate="Blade Runner", year=1982,
        edition_candidate="Remastered",
    )
    check(
        "Aliens.1986.Directors.Cut.1080p.BluRay.x265.mkv",
        media_type="movie", title_candidate="Aliens", year=1986,
        edition_candidate="Director's Cut",
    )
    check(
        "Rocky.IV.1985.Ultimate.Directors.Cut.4K.mkv",
        media_type="movie", title_candidate="Rocky IV", year=1985,
    )
    print("Alle FilenameIdentifier-Tests erfolgreich.")


if __name__ == "__main__":
    main()
