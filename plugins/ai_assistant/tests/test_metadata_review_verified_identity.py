from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "metadata_review_provider.py"

spec = importlib.util.spec_from_file_location(
    "metadata_review_provider",
    MODULE,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        f"Metadata-Review-Provider konnte nicht geladen werden: {MODULE}"
    )

metadata_review_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata_review_module)

MetadataAIReviewProvider = (
    metadata_review_module.MetadataAIReviewProvider
)


class BatchProvider:
    def analyze(self, payload):
        item = payload["items"][0]
        return {
            "items": [
                {
                    "media_type": "movie",
                    "suggested_name": (
                        "12 Monkeys (2020).mkv"
                    ),
                    "confidence": 0.88,
                    "warnings": [],
                    "structured_recommendation": {
                        "fields": {
                            "title": item.get("title"),
                            "year": item.get("year"),
                        }
                    },
                    "rationale": "Lokaler Altpfad.",
                }
            ]
        }


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(
        self,
        file_path,
        force=False,
        require_in_video=False,
        identity_hint=None,
    ):
        self.calls.append(
            {
                "path": str(file_path),
                "force": force,
                "require_in_video": (
                    require_in_video
                ),
                "identity_hint": dict(
                    identity_hint or {}
                ),
            }
        )

        in_video_state = (
            "completed"
            if require_in_video
            else "deferred"
        )

        return {
            "methods_used": [
                "filename",
                "ffprobe",
            ]
            + (
                ["ocr"]
                if require_in_video
                else []
            ),
            "in_video": {
                "state": in_video_state,
            },
            "integration": {
                "identity": {
                    "media_type": "movie",
                    "title": "12 Monkeys",
                    "year": 1995,
                    "confidence": 0.94,
                    "status": "probable",
                }
            },
        }


def test_wrong_container_year_triggers_in_video_and_loses(
    tmp_path,
):
    media = tmp_path / (
        "12 Monkeys 1995 Remastered "
        "1080p DL BD RX GER.mkv"
    )
    media.write_bytes(b"test")

    analyzer = FakeAnalyzer()
    provider = MetadataAIReviewProvider(
        BatchProvider(),
        analyzer,
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": (
                    "12 Monkeys 1995 Remastered "
                    "1080p DL BD RX GER"
                ),
                "year": 2020,
                "published_at": (
                    "2020-03-25T05:19:47.000000Z"
                ),
            },
        }
    )

    assert result["fields"]["media_type"] == "movie"
    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995

    assert result["changes"]["year"] == {
        "old": 2020,
        "new": 1995,
    }

    assert len(analyzer.calls) == 2
    assert analyzer.calls[0]["require_in_video"] is False
    assert analyzer.calls[1]["force"] is True
    assert (
        analyzer.calls[1]["require_in_video"]
        is True
    )

    assert (
        result["verification"]["in_video_state"]
        == "completed"
    )

    assert any(
        conflict["field"] == "year"
        for conflict in (
            result["verification"]["conflicts"]
        )
    ) is False


def test_matching_identity_does_not_force_second_analysis(
    tmp_path,
):
    media = tmp_path / "12 Monkeys 1995.mkv"
    media.write_bytes(b"test")

    analyzer = FakeAnalyzer()
    provider = MetadataAIReviewProvider(
        BatchProvider(),
        analyzer,
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": "12 Monkeys",
                "year": 1995,
            },
        }
    )

    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995
    assert len(analyzer.calls) == 1


def test_metadata_review_remains_read_only(
    tmp_path,
):
    media = tmp_path / "12 Monkeys 1995.mkv"
    media.write_bytes(b"test")

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        FakeAnalyzer(),
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": "12 Monkeys",
                "year": 1995,
            },
        }
    )

    assert result["execution_allowed"] is False
    assert result["metadata_write_allowed"] is False
    assert result["automatic_apply_allowed"] is False
    assert result["human_confirmation_required"] is True


class LowConfidenceAnalyzer:
    def analyze(
        self,
        file_path,
        force=False,
        require_in_video=False,
    ):
        return {
            "methods_used": [
                "filename",
                "ocr",
            ],
            "in_video": {
                "state": (
                    "completed"
                    if require_in_video
                    else "deferred"
                ),
            },
            "integration": {
                "identity": {
                    "media_type": "other",
                    "title": (
                        "AN ATLAS ENTERTAINMENT PRODUCTION"
                    ),
                    "year": None,
                    "confidence": 0.25,
                    "status": "insufficient",
                }
            },
        }


def test_low_confidence_ocr_identity_cannot_override(
    tmp_path,
):
    media = tmp_path / (
        "12 Monkeys 1995 Remastered "
        "1080p DL BD RX GER.mkv"
    )
    media.write_bytes(b"test")

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        LowConfidenceAnalyzer(),
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": "12 Monkeys",
                "year": 1995,
            },
        }
    )

    assert result["fields"]["media_type"] == "movie"
    assert (
        result["fields"]["title"]
        != "AN ATLAS ENTERTAINMENT PRODUCTION"
    )
    assert result["fields"]["year"] == 1995


def test_low_confidence_ocr_uses_movie_filename_identity(
    tmp_path,
):
    media = tmp_path / (
        "12 Monkeys 1995 Remastered "
        "1080p DL BD RX GER DTS-HDD-HDFreak79.mkv"
    )
    media.write_bytes(b"test")

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        LowConfidenceAnalyzer(),
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "",
                "title": (
                    "12 Monkeys 1995 Remastered "
                    "1080p DL BD RX GER DTS-HDD-HDFreak79"
                ),
                "year": 2020,
                "published_at": (
                    "2020-03-25T05:19:47.000000Z"
                ),
            },
        }
    )

    assert result["fields"]["media_type"] == "movie"
    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995
    assert result["fields"]["edition"] == "Remastered"

    assert result["changes"]["title"]["new"] == "12 Monkeys"
    assert result["changes"]["year"] == {
        "old": 2020,
        "new": 1995,
    }


def test_unverified_container_date_is_not_returned_as_release_date(
    tmp_path,
):
    media = tmp_path / "12 Monkeys 1995 Remastered.mkv"
    media.write_bytes(b"test")

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        LowConfidenceAnalyzer(),
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": "12 Monkeys",
                "year": 2020,
                "published_at": (
                    "2020-03-25T05:19:47.000000Z"
                ),
            },
        }
    )

    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995
    assert "published_at" not in result["fields"]
    assert "published_at" not in result["changes"]


def test_movie_identity_is_passed_to_media_analyzer(
    tmp_path,
):
    media = tmp_path / (
        "12.Monkeys.1995.GERMAN.1040p."
        "microHD.x264-Raistlin911.mkv"
    )
    media.write_bytes(b"test")

    analyzer = FakeAnalyzer()

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        analyzer,
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": (
                    "12 Monkeys 1995 Remastered "
                    "1080p DL BD RX GER DTS-HDD-HDFreak79"
                ),
                "year": 2020,
            },
        }
    )

    assert analyzer.calls

    first_call = analyzer.calls[0]
    hint = first_call["identity_hint"]

    assert hint["media_type"] == "movie"
    assert hint["title"] == "12 Monkeys"
    assert hint["year"] == 1995

    assert result["fields"]["media_type"] == "movie"
    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995


def test_existing_metadata_title_can_supply_movie_edition(
    tmp_path,
):
    media = tmp_path / (
        "12.Monkeys.1995.GERMAN.1040p."
        "microHD.x264-Raistlin911.mkv"
    )
    media.write_bytes(b"test")

    analyzer = FakeAnalyzer()

    provider = MetadataAIReviewProvider(
        BatchProvider(),
        analyzer,
    )

    result = provider.analyze(
        {
            "path": str(media),
            "item": {
                "path": str(media),
                "filename": media.name,
                "media_type": "movie",
                "title": (
                    "12 Monkeys 1995 Remastered "
                    "1080p DL BD RX GER DTS-HDD-HDFreak79"
                ),
                "year": 2020,
            },
        }
    )

    assert result["fields"]["media_type"] == "movie"
    assert result["fields"]["title"] == "12 Monkeys"
    assert result["fields"]["year"] == 1995
    assert result["fields"]["edition"] == "Remastered"

    assert result["changes"]["edition"] == {
        "old": None,
        "new": "Remastered",
    }
