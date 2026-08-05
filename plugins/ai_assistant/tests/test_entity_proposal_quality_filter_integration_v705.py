from pathlib import Path


def test_entity_proposal_quality_filter_integrated_v705():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.entity_proposal_quality_filter "
        "import EntityProposalQualityFilter"
        in text
    )
    assert (
        "self.entity_proposal_quality_filter = "
        "EntityProposalQualityFilter()"
        in text
    )
    assert (
        "entity_proposal_quality = "
        "self.entity_proposal_quality_filter.build("
        in text
    )
    assert (
        '"entity_proposal_quality": entity_proposal_quality'
        in text
    )
    assert (
        'context.document["entity_proposal_quality"] = '
        "entity_proposal_quality"
        in text
    )
