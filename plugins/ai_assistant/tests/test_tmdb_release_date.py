from pathlib import Path
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

import services.providers.tmdb_provider as tmdb_mod
from services.providers.tmdb_provider import TmdbProvider


def test_tmdb_search_exposes_release_date(monkeypatch):
    monkeypatch.setenv("MEDIAHUB_TMDB_API_KEY", "x")

    provider = TmdbProvider({
        "id": "tmdb",
        "name": "TMDb",
        "type": "tmdb",
        "enabled": True,
        "media_types": ["movie"],
        "language": "de-DE",
    })

    def fake(url, **kwargs):
        return {
            "results": [{
                "id": 63,
                "title": "12 Monkeys",
                "release_date": "1995-12-27",
                "vote_average": 8.0,
            }]
        }

    monkeypatch.setattr(tmdb_mod, "request_json", fake)

    result = provider.search({
        "title": "12 Monkeys",
        "media_type": "movie",
    })

    match = result.matches[0]

    assert match["year"] == 1995
    assert match["release_date"] == "1995-12-27"
    assert match["published_at"] == "1995-12-27"