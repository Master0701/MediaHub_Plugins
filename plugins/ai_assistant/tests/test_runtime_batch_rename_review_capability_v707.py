from pathlib import Path
from services.rename_review_provider import RenameReviewProvider
from services.batch_rename_review_provider import BatchRenameReviewProvider

def test_batch_review_keeps_mixed_media_types_separate():
    provider=BatchRenameReviewProvider(RenameReviewProvider())
    result=provider.analyze({
        "reference":{"media_type":"series","proposed_name":"Show - S01E01.mkv"},
        "schema":{"template":"[titel] - S[staffel]E[episode]"},
        "items":[
            {"media_type":"series","proposed_name":"Show - S01E02.mkv","renamer":{"media_type":"series","confidence":0.8}},
            {"media_type":"movie","proposed_name":"Film (2024).mkv","renamer":{"media_type":"movie","confidence":0.8}},
        ],
    })
    assert result["item_count"]==2
    assert result["groups"]=={"series":1,"movie":1}
    assert result["items"][1]["warnings"]
    assert result["execution_allowed"] is False
    assert result["metadata_write_allowed"] is False
