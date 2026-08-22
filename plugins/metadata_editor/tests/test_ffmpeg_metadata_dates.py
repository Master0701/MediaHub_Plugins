from plugins.metadata_editor.plugin import MediaHubMetadataEditorPlugin


def test_ffmpeg_published_at_has_priority_over_year():
    args = MediaHubMetadataEditorPlugin._ffmpeg_metadata_arguments(
        {
            "title": "Chappie",
            "year": 2016,
            "published_at": "2015-03-04",
        },
        {
            "title",
            "year",
            "published_at",
        },
    )

    pairs = list(zip(args[0::2], args[1::2]))

    assert ("-metadata", "title=Chappie") in pairs
    assert ("-metadata", "date=2015-03-04") in pairs

    # Wichtig: year darf das echte Veröffentlichungsdatum
    # nicht mehr als date überschreiben.
    assert ("-metadata", "date=2016") not in pairs


def test_ffmpeg_year_is_date_fallback_without_published_at():
    args = MediaHubMetadataEditorPlugin._ffmpeg_metadata_arguments(
        {
            "title": "Testfilm",
            "year": 2016,
            "published_at": "",
        },
        {
            "title",
            "year",
            "published_at",
        },
    )

    pairs = list(zip(args[0::2], args[1::2]))

    assert ("-metadata", "date=2016") in pairs
