from services.candidate_review_context import CandidateReviewContextService
from services.preview_presentation import PreviewPresentationService


def test_context_contains_candidates_and_stays_locked():
    payload={
        "original_name":"Batman.mkv",
        "proposed_name":"Batman.mkv",
        "source_path":"C:/Media/Batman.mkv",
        "media_type":"movie",
        "confidence":0.72,
        "review_required":True,
        "selected_candidate_id":"local-primary",
        "decision_state":"review_required",
        "decision_reason":"Mehrdeutig",
        "detection_candidates":[
            {"candidate_id":"local-primary","source":"local_filename","media_type":"movie","title":"Batman","confidence":0.72,"reasons":["Beste lokale Dateinamenanalyse"]},
            {"candidate_id":"local-video-unknown","source":"local_filename","media_type":"unknown","title":"Batman","confidence":0.54,"reasons":["Video ohne Jahr ist mehrdeutig"]},
        ],
    }
    result=CandidateReviewContextService().build(payload)
    assert result["candidate_count"]==2
    assert result["selected_candidate"]["candidate_id"]=="local-primary"
    assert result["renamer"]["review_required"] is True
    assert result["constraints"]["execution_allowed"] is False
    assert result["constraints"]["automatic_rename_allowed"] is False
    assert result["constraints"]["human_confirmation_required"] is True


def test_context_limits_candidates():
    result=CandidateReviewContextService().build({
        "detection_candidates":[{"candidate_id":str(i)} for i in range(20)]
    })
    assert result["candidate_count"]==8


def test_presentation_exposes_candidate_context():
    out=PreviewPresentationService().enrich({
        "media_items":[{
            "path":"C:/Media/Batman.mkv",
            "media_type":"movie",
            "detection_data":{
                "selected_candidate_id":"local-primary",
                "candidates":[
                    {"candidate_id":"local-primary","source":"local_filename","media_type":"movie","title":"Batman","confidence":0.72},
                    {"candidate_id":"local-video-unknown","source":"local_filename","media_type":"unknown","title":"Batman","confidence":0.54},
                ],
                "decision":{"state":"review_required","confidence":0.72,"review_required":True,"reason":"Mehrdeutig"},
            },
        }],
        "preview_rows":[{"source_path":"C:/Media/Batman.mkv","original_name":"Batman.mkv","proposed_name":"Batman.mkv"}],
    })
    row=out["preview_rows"][0]
    assert row["candidate_count"]==2
    assert row["selected_candidate_id"]=="local-primary"
    assert row["decision_state"]=="review_required"
    assert row["decision_reason"]=="Mehrdeutig"
    assert row["review_required"] is True
