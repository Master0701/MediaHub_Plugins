from services.batch_rename_review_provider import BatchRenameReviewProvider


class Single:
    def analyze(self,payload):
        return {
            "suggested_name":payload.get("proposed_name",""),
            "confidence":0.0,
            "rationale":"lokal",
            "warnings":[],
        }


def provider():
    return BatchRenameReviewProvider(Single())


def test_unknown_filename_with_sxxexx_becomes_series_and_uses_reference_title():
    result=provider().analyze({
        "reference":{
            "original_name":"lim-12monkeys-s03e02-480p.mkv",
            "proposed_name":"12 Monkeys - S03E02 - Wächter.mkv",
            "media_type":"series",
        },
        "items":[{
            "source_path":"D:/x/lim-12monkeys-s03e01-480p.mkv",
            "original_name":"lim-12monkeys-s03e01-480p.mkv",
            "media_type":"unknown",
            "proposed_name":"lim-12monkeys - S03E01 -.mkv",
        }],
    })
    item=result["items"][0]
    assert item["media_type"]=="series"
    assert item["suggested_name"]=="12 Monkeys - S03E01.mkv"
    assert item["reference_applied"] is True
    assert item["confidence"] >= 0.9
    assert not item["suggested_name"].endswith(" -.mkv")


def test_metadata_episode_title_is_added():
    result=provider().analyze({
        "reference":{
            "proposed_name":"12 Monkeys - S03E02 - Wächter.mkv",
            "media_type":"series",
        },
        "items":[{
            "source_path":"D:/x/lim-12monkeys-s03e01-480p.mkv",
            "original_name":"lim-12monkeys-s03e01-480p.mkv",
            "metadata_read":{
                "series_title":"12 Monkeys",
                "episode_title":"Mutter",
            },
        }],
    })
    item=result["items"][0]
    assert item["suggested_name"]=="12 Monkeys - S03E01 - Mutter.mkv"
    assert item["confidence"] >= 0.95


def test_movie_is_not_forced_into_series_reference():
    result=provider().analyze({
        "reference":{
            "proposed_name":"12 Monkeys - S03E02 - Wächter.mkv",
            "media_type":"series",
        },
        "items":[{
            "source_path":"D:/x/Blade.Runner.1982.1080p.mkv",
            "original_name":"Blade.Runner.1982.1080p.mkv",
            "metadata_read":{"title":"Blade Runner","year":"1982"},
        }],
    })
    item=result["items"][0]
    assert item["media_type"]=="movie"
    assert item["suggested_name"]=="Blade Runner (1982).mkv"
    assert item["reference_applied"] is False
    assert any("nicht blind" in x for x in item["warnings"])


def test_no_empty_trailing_separator_before_extension():
    result=provider().analyze({
        "items":[{
            "original_name":"show-s01e01-720p.mkv",
            "proposed_name":"Show - S01E01 -.mkv",
        }]
    })
    assert result["items"][0]["suggested_name"]=="Show - S01E01.mkv"
