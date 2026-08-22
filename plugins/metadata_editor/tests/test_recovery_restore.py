import json
from pathlib import Path

from plugins.metadata_editor.plugin import (
    MediaHubMetadataEditorPlugin,
)


def test_restore_latest_backup_restores_file(tmp_path):
    plugin = MediaHubMetadataEditorPlugin.__new__(
        MediaHubMetadataEditorPlugin
    )

    plugin.backup_dir = tmp_path / "backups"
    plugin.recovery_dir = tmp_path / "recovery"

    media = tmp_path / "movie.mp4"
    media.write_bytes(b"changed-version")

    backup = tmp_path / "original-backup.mp4"
    backup.write_bytes(b"original-version")

    plugin.recovery_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    recovery_file = (
        plugin.recovery_dir
        / "20260822_100000_movie-1.json"
    )

    recovery_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "action": "metadata.file.write",
                "item_id": "movie-1",
                "target": str(media),
                "backup": str(backup),
                "result": {
                    "ok": True,
                },
            }
        ),
        encoding="utf-8",
    )

    status, _, body = plugin.restore_latest_backup(
        {
            "item": {
                "id": "movie-1",
                "path": str(media),
            }
        }
    )

    data = json.loads(
        body.decode("utf-8")
    )

    assert status == 200
    assert data["ok"] is True
    assert media.read_bytes() == b"original-version"

    # Vor dem Restore muss die geänderte Version
    # ihrerseits nochmals gesichert worden sein.
    undo_backup = Path(
        data["undo_backup"]
    )

    assert undo_backup.is_file()
    assert undo_backup.read_bytes() == b"changed-version"

    # Auch der Restore selbst muss dokumentiert sein.
    restore_recovery = Path(
        data["recovery"]
    )

    assert restore_recovery.is_file()

    recorded = json.loads(
        restore_recovery.read_text(
            encoding="utf-8"
        )
    )

    assert recorded["action"] == "backup.restore"
    assert recorded["item_id"] == "movie-1"


def test_restore_latest_backup_without_backup_returns_404(
    tmp_path,
):
    plugin = MediaHubMetadataEditorPlugin.__new__(
        MediaHubMetadataEditorPlugin
    )

    plugin.backup_dir = tmp_path / "backups"
    plugin.recovery_dir = tmp_path / "recovery"

    media = tmp_path / "movie.mp4"
    media.write_bytes(b"current")

    status, _, body = plugin.restore_latest_backup(
        {
            "item": {
                "id": "movie-1",
                "path": str(media),
            }
        }
    )

    data = json.loads(
        body.decode("utf-8")
    )

    assert status == 404
    assert data["ok"] is False
