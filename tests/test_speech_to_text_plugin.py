from __future__ import annotations

import json
import zipfile
from pathlib import Path

import build_plugins

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "ai_node_plugins" / "speech_to_text"
MANIFEST = PLUGIN_DIR / "plugin.json"
AI_CATALOG = ROOT / "catalog" / "ai_plugin_catalog.json"


EXPECTED_SOURCE_FILES = {
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "requirements.txt",
    "engine.py",
    "execution.py",
    "pip_bootstrap.py",
    "plugin.json",
    "plugin.py",
    "python_provisioner.py",
    "python_runtime.py",
    "runtime.py",
    "runtime_bridge.py",
    "runtime_runner.py",
}


def _manifest() -> dict:
    return json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )


def test_speech_manifest_contract() -> None:
    data = _manifest()

    assert data["id"] == "mediahub.speech_to_text"
    assert data["type"] == "worker"
    assert (
        data["entrypoint"]
        == "plugin:MediaHubSpeechToTextPlugin"
    )
    assert data["api_version"] == "1"

    assert data["targets"] == [
        "raspberry_pi",
        "windows_compute",
    ]

    assert data["platforms"] == [
        "linux-aarch64",
        "windows-amd64",
    ]

    assert "speech_to_text" in data["capabilities"]
    assert "speech_to_text" in data["job_types"]


def test_speech_source_package_is_complete() -> None:
    files = {
        path.name
        for path in PLUGIN_DIR.iterdir()
        if path.is_file()
    }

    assert files == EXPECTED_SOURCE_FILES



def test_speech_ai_catalog_entry_matches_manifest() -> None:
    manifest = _manifest()

    catalog = json.loads(
        AI_CATALOG.read_text(encoding="utf-8")
    )

    entry = next(
        item
        for item in catalog["plugins"]
        if item["id"] == manifest["id"]
    )

    assert entry["version"] == manifest["version"]
    assert entry["type"] == manifest["type"]
    assert entry["targets"] == manifest["targets"]
    assert entry["platforms"] == manifest["platforms"]

    expected_asset = (
        "MediaHub_Speech-to-Text_"
        f"v{manifest['version']}.mhaiplugin"
    )

    assert entry["package_asset"] == expected_asset
    assert entry["release_asset"] == expected_asset
    assert (
        entry["sha256_asset"]
        == expected_asset + ".sha256"
    )


def test_speech_build_package_contains_expected_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        build_plugins,
        "RELEASE_DIR",
        tmp_path,
    )

    plugins = build_plugins.discover_ai_node_plugins()

    assert "speech_to_text" in plugins

    build_plugins.build_ai_node_plugin(
        "speech_to_text",
        plugins["speech_to_text"],
    )

    manifest = _manifest()

    package = (
        tmp_path
        / (
            "MediaHub_Speech-to-Text_"
            f"v{manifest['version']}.mhaiplugin"
        )
    )

    assert package.is_file()
    assert package.with_name(
        package.name + ".sha256"
    ).is_file()

    with zipfile.ZipFile(package, "r") as archive:
        names = set(archive.namelist())

    prefix = "mediahub.speech_to_text/"

    expected = {
        prefix + name
        for name in EXPECTED_SOURCE_FILES
    }

    assert names == expected

    assert not any(
        "__pycache__" in name
        or name.endswith(".pyc")
        for name in names
    )

def test_speech_engine_respects_max_segments(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import importlib.util
    import sys
    from types import SimpleNamespace

    engine_path = (
        PLUGIN_DIR
        / "engine.py"
    )

    spec = importlib.util.spec_from_file_location(
        "speech_engine_limit_test",
        engine_path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    media_file = (
        tmp_path
        / "sample.avi"
    )
    media_file.write_bytes(b"fake")

    segments = [
        SimpleNamespace(
            start=0.0,
            end=1.0,
            text="eins",
        ),
        SimpleNamespace(
            start=1.0,
            end=2.0,
            text="zwei",
        ),
        SimpleNamespace(
            start=2.0,
            end=3.0,
            text="drei",
        ),
    ]

    class FakeModel:
        def __init__(
            self,
            *args,
            **kwargs,
        ) -> None:
            pass

        def transcribe(
            self,
            *args,
            **kwargs,
        ):
            return (
                iter(segments),
                SimpleNamespace(
                    language="de",
                    language_probability=0.99,
                ),
            )

    fake_module = SimpleNamespace(
        WhisperModel=FakeModel
    )

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        fake_module,
    )

    result = (
        module._faster_whisper_transcribe(
            path=media_file,
            execution={
                "backend": "cpu",
                "cpu_threads": 2,
            },
            options={
                "max_segments": 2,
            },
        )
    )

    assert len(result["segments"]) == 2
    assert result["text"] == "eins zwei"
    assert result["truncated"] is True
    assert (
        result["truncation_reason"]
        == "max_segments"
    )
    assert (
        result["limits"]["max_segments"]
        == 2
    )

def test_speech_engine_respects_max_audio_seconds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import importlib.util
    import sys
    from types import SimpleNamespace

    engine_path = (
        PLUGIN_DIR
        / "engine.py"
    )

    spec = importlib.util.spec_from_file_location(
        "speech_engine_time_limit_test",
        engine_path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    media_file = (
        tmp_path
        / "sample.avi"
    )
    media_file.write_bytes(b"fake")

    segments = [
        SimpleNamespace(
            start=0.0,
            end=10.0,
            text="eins",
        ),
        SimpleNamespace(
            start=10.0,
            end=20.0,
            text="zwei",
        ),
        SimpleNamespace(
            start=25.0,
            end=30.0,
            text="drei",
        ),
    ]

    class FakeModel:
        def __init__(
            self,
            *args,
            **kwargs,
        ) -> None:
            pass

        def transcribe(
            self,
            *args,
            **kwargs,
        ):
            return (
                iter(segments),
                SimpleNamespace(
                    language="de",
                    language_probability=0.99,
                ),
            )

    fake_module = SimpleNamespace(
        WhisperModel=FakeModel
    )

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        fake_module,
    )

    result = (
        module._faster_whisper_transcribe(
            path=media_file,
            execution={
                "backend": "cpu",
                "cpu_threads": 2,
            },
            options={
                "max_audio_seconds": 20,
            },
        )
    )

    assert len(result["segments"]) == 2
    assert result["text"] == "eins zwei"
    assert result["truncated"] is True
    assert (
        result["truncation_reason"]
        == "max_audio_seconds"
    )
    assert (
        result["limits"]["max_audio_seconds"]
        == 20.0
    )

