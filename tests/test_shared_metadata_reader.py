from mediahub_metadata_core import normalize_tags


def test_mp4_basic_metadata():
    result = normalize_tags(
        ".mp4",
        {
            "title": "Testfilm",
            "description": "Beschreibung",
            "date": "1999",
        },
    )

    assert result["title"] == "Testfilm"
    assert result["description"] == "Beschreibung"
    assert result["year"] == 1999


def test_series_metadata():
    result = normalize_tags(
        ".mkv",
        {
            "title": "Pilot",
            "show": "Testserie",
            "season_number": "2",
            "episode_sort": "7",
        },
    )

    assert result["title"] == "Pilot"
    assert result["series"] == "Testserie"
    assert result["season"] == 2
    assert result["episode"] == 7


def test_audio_metadata():
    result = normalize_tags(
        ".mp3",
        {
            "title": "Kapitel 1",
            "artist": "Max Mustermann",
            "album": "Testh?rbuch",
            "track": "3/12",
            "genre": "Audiobook",
        },
    )

    assert result["title"] == "Kapitel 1"
    assert result["artist"] == "Max Mustermann"
    assert result["album"] == "Testh?rbuch"
    assert result["track"] == 3
    assert result["genre"] == "Audiobook"


def test_m4b_audiobook_metadata():
    result = normalize_tags(
        ".m4b",
        {
            "title": "Mein H?rbuch",
            "artist": "Autor",
            "narrator": "Sprecher",
            "publisher": "Verlag",
        },
    )

    assert result["title"] == "Mein H?rbuch"
    assert result["author"] == "Autor"
    assert result["narrator"] == "Sprecher"
    assert result["publisher"] == "Verlag"


def test_unknown_format_reads_nothing():
    assert normalize_tags(
        ".xyz",
        {"title": "Nicht ?bernehmen"},
    ) == {}
