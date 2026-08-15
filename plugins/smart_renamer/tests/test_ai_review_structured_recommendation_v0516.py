from services.ai_review_recommendation import AIReviewRecommendationService


def context():
    return {
        "candidates":[
            {
                "candidate_id":"movie-1989",
                "media_type":"movie",
                "title":"Batman",
                "year":"1989",
                "confidence":0.82,
            },
            {
                "candidate_id":"movie-2022",
                "media_type":"movie",
                "title":"The Batman",
                "year":"2022",
                "confidence":0.78,
            },
        ]
    }


def test_valid_candidate_id_is_resolved_and_fields_filled():
    result=AIReviewRecommendationService().normalize(
        {
            "candidate_id":"movie-1989",
            "confidence":0.91,
            "rationale":"Passt am besten zu den vorhandenen Hinweisen.",
        },
        context(),
    )
    assert result["candidate_valid"] is True
    assert result["candidate_id"]=="movie-1989"
    assert result["fields"]["title"]=="Batman"
    assert result["fields"]["year"]=="1989"
    assert result["confidence"]==0.91
    assert result["execution_allowed"] is False
    assert result["automatic_apply_allowed"] is False
    assert result["human_confirmation_required"] is True


def test_invalid_candidate_id_is_rejected_not_silently_accepted():
    result=AIReviewRecommendationService().normalize(
        {"candidate_id":"invented","confidence":0.99},
        context(),
    )
    assert result["candidate_valid"] is False
    assert result["candidate_id"]==""
    assert result["warnings"]


def test_structured_fields_may_override_candidate_for_review_only():
    result=AIReviewRecommendationService().normalize(
        {
            "structured_recommendation":{
                "candidate_id":"movie-2022",
                "title":"The Batman",
                "year":"2022",
                "edition":"IMAX",
                "confidence":0.88,
                "rationale":"Edition im Dateinamen erkannt.",
            }
        },
        context(),
    )
    assert result["candidate_valid"] is True
    assert result["fields"]["title"]=="The Batman"
    assert result["fields"]["edition"]=="IMAX"
    assert result["advisory_only"] is True
