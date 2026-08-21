from pathlib import Path
from types import SimpleNamespace

import plugins.metadata_editor.plugin as plugin_mod


def test_mkv_writer_adds_poster_attachment(monkeypatch, tmp_path):
    media = tmp_path / "movie.mkv"
    media.write_bytes(b"dummy")

    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"jpeg")

    tag_file = tmp_path / "tags.xml"
    tag_file.write_text("<Tags></Tags>", encoding="utf-8")

    plugin = plugin_mod.MediaHubMetadataEditorPlugin.__new__(
        plugin_mod.MediaHubMetadataEditorPlugin
    )

    plugin.recovery_dir = tmp_path
    plugin._mkvpropedit_path = lambda: Path("mkvpropedit.exe")
    plugin._mkvextract_path = lambda: Path("mkvextract.exe")
    plugin._poster_path = lambda edited: poster

    plugin._extract_mkv_tags = lambda media_path, output_path: {
        "ok": True,
        "xml": "<Tags></Tags>",
    }

    plugin._backup_file = lambda *args, **kwargs: tmp_path / "backup.mkv"
    plugin._record_recovery = lambda **kwargs: tmp_path / "recovery.json"

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        plugin_mod.subprocess,
        "run",
        fake_run,
    )

    result = plugin._write_mkv_metadata(
        item_id="movie-1",
        media_path=media,
        original={
            "title": "Alt",
        },
        edited={
            "title": "Neu",
            "description": "Beschreibung",
            "poster_path": str(poster),
        },
        capability={
            "write_fields": (
                "title",
                "description",
            ),
        },
    )

    assert result["ok"] is True
    assert result["written"] is True

    assert len(commands) == 1
    command = commands[0]

    assert "--add-attachment" in command
    assert str(poster) in command

    name_index = command.index("--attachment-name")
    assert command[name_index + 1] == "cover.jpg"

    mime_index = command.index("--attachment-mime-type")
    assert command[mime_index + 1] == "image/jpeg"

    assert "--delete-attachment" in command
