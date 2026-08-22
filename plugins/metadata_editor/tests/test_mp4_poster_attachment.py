import json
from pathlib import Path
from types import SimpleNamespace

import plugins.metadata_editor.plugin as plugin_mod


def _make_plugin(tmp_path, poster):
    plugin = plugin_mod.MediaHubMetadataEditorPlugin.__new__(
        plugin_mod.MediaHubMetadataEditorPlugin
    )

    plugin.recovery_dir = tmp_path

    plugin._tool_path = lambda tool_id: {
        "ffmpeg": Path("ffmpeg.exe"),
        "ffprobe": Path("ffprobe.exe"),
    }.get(tool_id)

    plugin._poster_path = lambda edited: poster

    plugin._backup_file = (
        lambda *args, **kwargs:
        tmp_path / "backup.mp4"
    )

    plugin._record_recovery = (
        lambda **kwargs:
        tmp_path / "recovery.json"
    )

    return plugin


def test_mp4_writer_embeds_poster_as_attached_pic(
    monkeypatch,
    tmp_path,
):
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"original-mp4")

    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"jpeg-poster")

    plugin = _make_plugin(tmp_path, poster)

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)

        if command[0] == "ffprobe.exe":
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [
                            {
                                "index": 0,
                                "codec_type": "video",
                                "disposition": {
                                    "attached_pic": 0,
                                },
                            },
                            {
                                "index": 1,
                                "codec_type": "audio",
                                "disposition": {
                                    "attached_pic": 0,
                                },
                            },
                        ],
                    }
                ),
                stderr="",
            )

        output = Path(command[-1])
        output.write_bytes(b"new-mp4-with-poster")

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

    result = plugin._write_embedded_metadata(
        item_id="movie-1",
        media_path=media,
        original={
            "title": "Alt",
            "source_type": "local_folder",
        },
        edited={
            "title": "Neu",
            "description": "Beschreibung",
            "poster_path": str(poster),
        },
    )

    assert result["ok"] is True
    assert result["written"] is True
    assert len(commands) == 2

    probe_command = commands[0]
    command = commands[1]

    assert probe_command[0] == "ffprobe.exe"
    assert "0:0" in command
    assert "0:1" in command
    assert "1:0" in command

    codec_index = command.index("-c")
    assert command[codec_index + 1] == "copy"

    assert "-disposition:v:1" in command
    disposition_index = command.index("-disposition:v:1")
    assert command[disposition_index + 1] == "attached_pic"

    assert "-metadata:s:v:1" in command
    assert "title=MediaHub Poster" in command
    assert "comment=Cover (front)" in command
    assert media.read_bytes() == b"new-mp4-with-poster"


def test_mp4_writer_handles_multiple_video_streams_and_replaces_old_cover(
    monkeypatch,
    tmp_path,
):
    media = tmp_path / "multi-video.mp4"
    media.write_bytes(b"original-multi-video")

    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"jpeg-poster")

    plugin = _make_plugin(tmp_path, poster)

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)

        if command[0] == "ffprobe.exe":
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [
                            {
                                "index": 0,
                                "codec_type": "video",
                                "disposition": {"attached_pic": 0},
                            },
                            {
                                "index": 1,
                                "codec_type": "video",
                                "disposition": {"attached_pic": 0},
                            },
                            {
                                "index": 2,
                                "codec_type": "audio",
                                "disposition": {"attached_pic": 0},
                            },
                            {
                                "index": 3,
                                "codec_type": "video",
                                "disposition": {"attached_pic": 1},
                            },
                            {
                                "index": 4,
                                "codec_type": "subtitle",
                                "disposition": {"attached_pic": 0},
                            },
                        ],
                    }
                ),
                stderr="",
            )

        output = Path(command[-1])
        output.write_bytes(b"new-multi-video-with-poster")

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

    result = plugin._write_embedded_metadata(
        item_id="movie-2",
        media_path=media,
        original={
            "title": "Alt",
            "source_type": "local_folder",
        },
        edited={
            "title": "Neu",
            "poster_path": str(poster),
        },
    )

    assert result["ok"] is True
    assert len(commands) == 2

    command = commands[1]

    assert "0:0" in command
    assert "0:1" in command
    assert "0:2" in command
    assert "0:4" in command
    assert "0:3" not in command
    assert "1:0" in command

    assert "-disposition:v:2" in command
    disposition_index = command.index("-disposition:v:2")
    assert command[disposition_index + 1] == "attached_pic"

    assert "-metadata:s:v:2" in command
    assert media.read_bytes() == b"new-multi-video-with-poster"
