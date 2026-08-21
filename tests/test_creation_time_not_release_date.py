from shared.mediahub_metadata_core.reader import normalize_tags


def test_mkv_creation_time_is_not_movie_release_date():
    result = normalize_tags(
        ".mkv",
        {
            "title": "12 Monkeys",
            "creation_time": "2020-03-25T05:19:47.000000Z",
        },
    )

    assert result["title"] == "12 Monkeys"
    assert "year" not in result
    assert "published_at" not in result


def test_mkv_real_date_can_supply_release_year():
    result = normalize_tags(
        ".mkv",
        {
            "date": "1995-12-27",
        },
    )

    assert result["year"] == 1995
    assert result["published_at"] == "1995-12-27"


def test_explicit_year_has_priority_over_date():
    result = normalize_tags(
        ".mkv",
        {
            "year": "1995",
            "date": "2020-03-25",
        },
    )

    assert result["year"] == 1995
