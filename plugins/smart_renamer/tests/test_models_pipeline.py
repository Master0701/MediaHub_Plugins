from pathlib import Path

from models.media_item import MediaItem
from models.preview import PreviewIssue, PreviewRow, Severity
from services.backend_registry import RenamerBackendRegistry
from services.preview_service import RenamePreviewService


def test_media_item_maps_common_fields(tmp_path: Path):
    source = tmp_path / "Film.mkv"
    source.write_text("x", encoding="utf-8")
    item = MediaItem.from_path(source, metadata={"jahr": "2024"})

    assert item.name == "Film.mkv"
    assert item.title == "Film"
    assert item.year == "2024"
    assert item.rule_metadata()["titel"] == "Film"


def test_preview_row_blocking_state():
    row = PreviewRow(
        index=0,
        source_path="a.mkv",
        original_name="a.mkv",
        proposed_name="b.mkv",
        target_path="b.mkv",
        changed=True,
        item_type="file",
        backend_id="mediahub_native",
        issues=[
            PreviewIssue(
                code="duplicate_target",
                message="Doppelt",
                severity=Severity.BLOCKING,
            )
        ],
    )
    assert row.blocked is True
    assert row.highest_severity == Severity.BLOCKING


def test_pipeline_returns_media_and_preview_models(tmp_path: Path):
    source = tmp_path / "Film  2024.mkv"
    source.write_text("x", encoding="utf-8")
    service = RenamePreviewService(RenamerBackendRegistry(base_dir=tmp_path))
    result = service.create_preview(
        items=[{"path": str(source), "metadata": {"jahr": "2024"}}],
        rules=[{"type": "trim"}],
    )

    assert result["status"] == "preview_ready"
    assert result["media_items"][0]["year"] == "2024"
    assert result["preview_rows"][0]["highest_severity"] == "info"
