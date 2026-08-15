from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/"services"/"metadata_review_provider.py"

spec=importlib.util.spec_from_file_location("metadata_review_provider", MODULE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Provider=mod.MetadataAIReviewProvider


class Batch:
    def __init__(self):
        self.payload=None

    def analyze(self,payload):
        self.payload=payload
        reference=payload.get("reference") or {}
        return {
            "items":[{
                "media_type":"series",
                "suggested_name":reference.get("proposed_name","12 Monkeys - S02E04.mkv"),
                "episode_title":"",
                "confidence":0.92,
                "warnings":[],
            }]
        }


def test_raw_filename_identity_is_clean():
    info=Provider._filename_identity("lim-12monkeys-s02e04-sd.mkv")
    assert info["series"]=="12monkeys"
    assert info["season"]==2
    assert info["episode"]==4


def test_spaced_episode_marker_is_clean():
    info=Provider._filename_identity("Lim-12 Monkeys-s 02 E 04-sd.mkv")
    assert info["series"]=="12 Monkeys"
    assert info["season"]==2
    assert info["episode"]==4


def test_clean_reference_is_sent_to_batch_provider():
    batch=Batch()
    provider=Provider(batch)
    result=provider.analyze({
        "item":{
            "filename":"lim-12monkeys-s02e04-sd.mkv",
            "path":"D:/Serien/lim-12monkeys-s02e04-sd.mkv",
        }
    })
    reference=batch.payload["reference"]
    assert reference["media_type"]=="series"
    assert reference["proposed_name"]=="12monkeys - S02E04.mkv"
    assert result["fields"]["series"]=="12monkeys"
    assert result["fields"]["season"]==2
    assert result["fields"]["episode"]==4


def test_release_prefix_does_not_become_series_title():
    batch=Batch()
    provider=Provider(batch)
    result=provider.analyze({
        "item":{"filename":"Lim-12 Monkeys-s 02 E 04-sd.mkv"}
    })
    assert result["fields"]["series"]=="12 Monkeys"
    assert not result["fields"]["series"].casefold().startswith("lim")
