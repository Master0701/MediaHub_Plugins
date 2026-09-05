from services.online_result_ranker import OnlineResultRanker


def test_ranker_preserves_tmdb_visual_references():
    ranker = OnlineResultRanker()

    result = ranker.rank(
        {
            "title": "Aquaman and the Lost Kingdom",
            "media_type": "movie",
            "year": 2023,
        },
        [
            {
                "provider_id": "tmdb",
                "provider_name": "TMDb",
                "trust": 0.95,
                "priority": 90,
                "matches": [
                    {
                        "external_id": "572802",
                        "title": "Aquaman and the Lost Kingdom",
                        "original_title": (
                            "Aquaman and the Lost Kingdom"
                        ),
                        "year": 2023,
                        "media_type": "movie",
                        "provider_confidence": 0.7,
                        "raw": {
                            "id": 572802,
                            "poster_path": "/poster.jpg",
                            "backdrop_path": "/backdrop.jpg",
                        },
                    }
                ],
            }
        ],
    )

    best = result["best_match"]

    assert best["external_id"] == "572802"
    assert best["raw"]["poster_path"] == "/poster.jpg"
    assert best["raw"]["backdrop_path"] == "/backdrop.jpg"


def test_ranker_preserves_tvdb_visual_references():
    ranker = OnlineResultRanker()

    result = ranker.rank(
        {
            "title": "Example Movie",
            "media_type": "movie",
            "year": 2023,
        },
        [
            {
                "provider_id": "tvdb",
                "provider_name": "TheTVDB",
                "trust": 0.90,
                "priority": 80,
                "matches": [
                    {
                        "external_id": "123",
                        "title": "Example Movie",
                        "year": 2023,
                        "media_type": "movie",
                        "raw": {
                            "tvdb_id": "123",
                            "image_url": (
                                "https://example.invalid/image.jpg"
                            ),
                            "poster_url": (
                                "https://example.invalid/poster.jpg"
                            ),
                        },
                    }
                ],
            }
        ],
    )

    best = result["best_match"]

    assert best["external_id"] == "123"
    assert (
        best["raw"]["image_url"]
        == "https://example.invalid/image.jpg"
    )
    assert (
        best["raw"]["poster_url"]
        == "https://example.invalid/poster.jpg"
    )
