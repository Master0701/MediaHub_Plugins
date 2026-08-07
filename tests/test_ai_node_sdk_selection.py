from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from shared.ai_node_sdk import (
    LoadedPlugin,
    SelectionPolicy,
    TaskRequest,
    find_candidates,
    load_plugin,
    route_task,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "ai_node_plugins"
    / "mediahub_test_provider"
    / "plugin.json"
)


class FailingProvider:
    plugin_id = "provider.failing"
    name = "Failing Provider"
    version = "1.0.0"

    def test(self, value):
        raise RuntimeError("absichtlicher Testfehler")


def _plugins():
    working = load_plugin(MANIFEST)

    failing_manifest = replace(
        working.manifest,
        plugin_id="provider.failing",
        name="Failing Provider",
    )
    failing = LoadedPlugin(
        manifest=failing_manifest,
        instance=FailingProvider(),
        module=working.module,
        plugin_root=working.plugin_root,
    )
    return working, failing


def test_priority_orders_usable_candidates():
    working, failing = _plugins()

    candidates = find_candidates(
        [working, failing],
        "test_provider",
        policy=SelectionPolicy(
            priorities={
                "provider.failing": 50,
                "provider.mediahub_test": 10,
            }
        ),
    )

    assert [item.plugin_id for item in candidates] == [
        "provider.failing",
        "provider.mediahub_test",
    ]


def test_fallback_uses_next_plugin_after_execution_failure():
    working, failing = _plugins()

    result = route_task(
        [working, failing],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "Fallback"},
        ),
        policy=SelectionPolicy(
            priorities={
                "provider.failing": 100,
                "provider.mediahub_test": 10,
            },
            allow_fallback=True,
        ),
    )

    assert result.ok is True
    assert result.backend == "provider.mediahub_test"
    assert result.data["value"] == "Fallback"
    assert result.metadata["fallback_index"] == 1


def test_fallback_can_be_disabled():
    working, failing = _plugins()

    result = route_task(
        [working, failing],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "NoFallback"},
        ),
        policy=SelectionPolicy(
            priorities={
                "provider.failing": 100,
                "provider.mediahub_test": 10,
            },
            allow_fallback=False,
        ),
    )

    assert result.ok is False
    assert result.metadata["attempt_count"] == 1


def test_explicit_preference_breaks_equal_priority():
    working, failing = _plugins()

    candidates = find_candidates(
        [working, failing],
        "test_provider",
        policy=SelectionPolicy(
            preferred_plugin_ids=(
                "provider.mediahub_test",
                "provider.failing",
            ),
            priorities={
                "provider.failing": 10,
                "provider.mediahub_test": 10,
            },
        ),
    )

    assert candidates[0].plugin_id == "provider.mediahub_test"
