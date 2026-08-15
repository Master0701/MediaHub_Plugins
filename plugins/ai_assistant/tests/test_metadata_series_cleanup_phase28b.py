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
        ref=payload.get("reference") or {}
        return {
            "items":[{
                "media_type":"series",
                "suggested_name":ref.get("proposed_name","12 Monkeys - S01E07.mkv"),
                "episode_title":"",
                "confidence":0.92,
                "warnings":[],
                "rationale":"test",
            }]
        }


def test_dirty_existing_series_metadata_is_cleaned():
    batch=Batch()
    provider=Provider(batch)
    result=provider.analyze({
        "item":{
            "filename":"rsg-12-monkeys-s01e07-sd.mkv",
            "series":"Rsg-12-monkeys-s 01 E 07-sd",
        }
    })
    assert result["fields"]["series"]=="12 Monkeys"
    assert result["fields"]["season"]==1
    assert result["fields"]["episode"]==7

    sent=batch.payload["items"][0]
    assert sent["series"]=="12 Monkeys"
    assert sent["series_title"]=="12 Monkeys"


def test_clean_existing_series_metadata_stays_clean():
    batch=Batch()
    provider=Provider(batch)
    result=provider.analyze({
        "item":{
            "filename":"rsg-12-monkeys-s01e07-sd.mkv",
            "series":"12 Monkeys",
        }
    })
    assert result["fields"]["series"]=="12 Monkeys"


def test_lim_dirty_metadata_is_cleaned_too():
    batch=Batch()
    provider=Provider(batch)
    result=provider.analyze({
        "item":{
            "filename":"lim-12monkeys-s02e04-sd.mkv",
            "series":"Lim-12 Monkeys-s 02 E 04-sd",
        }
    })
    assert result["fields"]["series"]=="12 Monkeys"
    assert result["fields"]["season"]==2
    assert result["fields"]["episode"]==4
