from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.online_result_ranker import OnlineResultRanker
from services.providers.tmdb_provider import TmdbProvider


def _fake_request_json(url, params=None, headers=None):
    if url.endswith("/search/movie"):
        return {
            "results": [
                {
                    "id": 137113,
                    "title": "Edge of Tomorrow",
                    "original_title": "Edge of Tomorrow",
                    "release_date": "2014-05-27",
                    "media_type": "movie",
                    "overview": "Testbeschreibung",
                    "original_language": "en",
                    "popularity": 100.0,
                    "vote_average": 7.6,
                    "poster_path": "/test.jpg",
                }
            ]
        }

    if url.endswith(
        "/movie/137113/alternative_titles"
    ):
        return {
            "id": 137113,
            "titles": [
                {
                    "iso_3166_1": "US",
                    "title": "Live Die Repeat",
                    "type": "",
                },
                {
                    "iso_3166_1": "US",
                    "title": "Edge of Tomorrow",
                    "type": "",
                },
                {
                    "iso_3166_1": "DE",
                    "title": "Live Die Repeat",
                    "type": "",
                },
            ],
        }

    raise AssertionError(
        f"Unerwarteter TMDb-Aufruf: {url}"
    )


def test_tmdb_alternative_title_reaches_ranker():
    old_token = os.environ.get(
        "MEDIAHUB_TMDB_BEARER_TOKEN"
    )

    os.environ[
        "MEDIAHUB_TMDB_BEARER_TOKEN"
    ] = "mock-token"

    try:
        provider = TmdbProvider(
            {
                "id": "tmdb",
                "name": "TMDb",
                "type": "tmdb",
                "enabled": True,
                "trust": 0.95,
                "priority": 95,
                "language": "de-DE",
            }
        )

        with patch(
            "services.providers.tmdb_provider."
            "request_json",
            side_effect=_fake_request_json,
        ):
            result = provider.search(
                {
                    "title": "Live Die Repeat",
                    "media_type": "movie",
                    "year": 2014,
                }
            )

        assert result.status == "ok"
        assert len(result.matches) == 1

        match = result.matches[0]

        assert match["title"] == "Edge of Tomorrow"
        assert match["year"] == 2014
        assert match["aliases"] == [
            "Live Die Repeat"
        ]

        ranker = OnlineResultRanker()

        ranking = ranker.rank(
            {
                "title": "Live Die Repeat",
                "media_type": "movie",
                "year": 2014,
            },
            [
                {
                    "provider_id": "tmdb",
                    "provider_name": "TMDb",
                    "trust": 0.95,
                    "priority": 95,
                    "matches": [
                        {
                            **match,
                            "search_variant":
                                "Live Die Repeat",
                            "search_variant_score": 1.0,
                        }
                    ],
                }
            ],
        )

        best = ranking["best_match"]

        assert best is not None
        assert best["title"] == "Edge of Tomorrow"
        assert (
            best["score_details"]["exact_alias"]
            is True
        )
        assert best["evidence_count"] >= 3
        assert best["score"] >= 0.72
        assert ranking["decision"] in {
            "probable_match",
            "strong_match",
        }

    finally:
        if old_token is None:
            os.environ.pop(
                "MEDIAHUB_TMDB_BEARER_TOKEN",
                None,
            )
        else:
            os.environ[
                "MEDIAHUB_TMDB_BEARER_TOKEN"
            ] = old_token
