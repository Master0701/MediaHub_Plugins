from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_repository_license_files_exist():
    assert (ROOT / "LICENSE").is_file()
    assert (
        ROOT
        / "THIRD_PARTY_LICENSES.md"
    ).is_file()


def test_mediahub_plugins_are_proprietary():
    manifests = sorted(
        (ROOT / "plugins")
        .glob("*/plugin.json")
    )

    assert manifests

    for manifest in manifests:
        data = load_manifest(manifest)

        license_data = data.get("license")

        assert isinstance(
            license_data,
            dict,
        ), manifest

        assert (
            license_data.get(
                "project_license"
            )
            == "Proprietary"
        ), manifest

        assert isinstance(
            license_data.get(
                "third_party_licenses"
            ),
            list,
        ), manifest


def test_no_mediahub_license_contains_tbd():

    for manifest in sorted(
        (ROOT / "plugins")
        .glob("*/plugin.json")
    ):
        data = load_manifest(manifest)

        license_text = json.dumps(
            data.get("license"),
            ensure_ascii=False,
        ).casefold()

        assert "tbd" not in license_text


def test_ai_node_plugins_have_license():

    for manifest in sorted(
        (ROOT / "ai_node_plugins")
        .glob("*/plugin.json")
    ):
        data = load_manifest(manifest)

        value = data.get("license")

        if isinstance(value, dict):
            value = value.get(
                "project_license"
            )

        assert str(value or "").strip()
        assert (
            str(value)
            .strip()
            .casefold()
            != "tbd"
        )


def test_ai_node_test_provider_stays_mit():

    manifest = (
        ROOT
        / "ai_node_plugins"
        / "mediahub_test_provider"
        / "plugin.json"
    )

    data = load_manifest(manifest)

    assert data["license"] == "MIT"


def test_smart_renamer_keeps_renamer_license():

    manifest = (
        ROOT
        / "plugins"
        / "smart_renamer"
        / "plugin.json"
    )

    data = load_manifest(manifest)

    entries = (
        data["license"]
        ["third_party_licenses"]
    )

    renamer = next(
        entry
        for entry in entries
        if entry.get("name")
        == "ReNamer"
    )

    assert renamer["bundled"] is False
    assert renamer["vendor"]
    assert renamer["homepage"]
    assert renamer["download"]
    assert renamer["license"]
