from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .manifest import PluginManifest, load_manifest
from .plugin_api import supports_health


@dataclass(frozen=True, slots=True)
class LoadedPlugin:
    manifest: PluginManifest
    instance: object
    module: ModuleType
    plugin_root: Path

    @property
    def capabilities(self) -> tuple[str, ...]:
        return self.manifest.capability_names

    def has_capability(self, name: str) -> bool:
        return str(name).strip() in self.capabilities


def _resolve_entrypoint(
    plugin_root: Path,
    entrypoint: str,
) -> tuple[Path, str, str]:
    if ":" not in entrypoint:
        raise ValueError(
            "entrypoint muss das Format 'modul:Objekt' verwenden."
        )

    module_name, object_name = (
        part.strip()
        for part in entrypoint.split(":", 1)
    )

    if not module_name or not object_name:
        raise ValueError(
            "entrypoint muss Modul und Objekt enthalten."
        )

    module_path = plugin_root / (
        module_name.replace(".", "/") + ".py"
    )

    if not module_path.is_file():
        raise FileNotFoundError(
            f"Entrypoint-Modul nicht gefunden: {module_path}"
        )

    return module_path, module_name, object_name


def load_plugin(
    manifest_path: str | Path,
) -> LoadedPlugin:
    path = Path(manifest_path).resolve()
    manifest = load_manifest(path)

    if not manifest.api_supported:
        raise RuntimeError(
            f"Plugin-API {manifest.api_version} wird vom SDK "
            "nicht unterstützt."
        )

    plugin_root = path.parent
    module_path, module_name, object_name = _resolve_entrypoint(
        plugin_root,
        manifest.entrypoint,
    )

    import_name = (
        "mediahub_ai_node_plugin_"
        + manifest.plugin_id.replace(".", "_").replace("-", "_")
    )

    spec = importlib.util.spec_from_file_location(
        import_name,
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Plugin-Modul konnte nicht geladen werden: {module_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(import_name, None)
        raise

    target = getattr(module, object_name, None)
    if target is None:
        raise RuntimeError(
            f"Entrypoint-Objekt fehlt: {module_name}:{object_name}"
        )

    instance = target() if callable(target) else target

    loaded = LoadedPlugin(
        manifest=manifest,
        instance=instance,
        module=module,
        plugin_root=plugin_root,
    )

    validate_loaded_plugin(loaded)
    return loaded


def validate_loaded_plugin(plugin: LoadedPlugin) -> None:
    manifest = plugin.manifest
    instance = plugin.instance

    runtime_id = getattr(instance, "plugin_id", manifest.plugin_id)
    runtime_name = getattr(instance, "name", manifest.name)
    runtime_version = getattr(instance, "version", manifest.version)

    if str(runtime_id) != manifest.plugin_id:
        raise RuntimeError(
            f"Runtime-ID stimmt nicht mit Manifest überein: "
            f"{runtime_id} != {manifest.plugin_id}"
        )

    if str(runtime_name) != manifest.name:
        raise RuntimeError(
            f"Runtime-Name stimmt nicht mit Manifest überein: "
            f"{runtime_name} != {manifest.name}"
        )

    if str(runtime_version) != manifest.version:
        raise RuntimeError(
            f"Runtime-Version stimmt nicht mit Manifest überein: "
            f"{runtime_version} != {manifest.version}"
        )

    if (
        "health_check" in manifest.capability_names
        and not supports_health(instance)
    ):
        raise RuntimeError(
            "Capability 'health_check' ist deklariert, "
            "aber health() fehlt."
        )


def read_health(plugin: LoadedPlugin) -> dict[str, Any]:
    if not supports_health(plugin.instance):
        raise RuntimeError(
            f"{plugin.manifest.name} stellt keine health()-Methode bereit."
        )

    result = plugin.instance.health()

    if not isinstance(result, dict):
        raise RuntimeError(
            "health() muss ein Dictionary zurückgeben."
        )

    required = ("status", "plugin_id", "plugin", "version")
    missing = [
        field
        for field in required
        if not str(result.get(field, "")).strip()
    ]
    if missing:
        raise RuntimeError(
            "health()-Antwort enthält nicht alle Pflichtfelder: "
            + ", ".join(missing)
        )

    if str(result["plugin_id"]) != plugin.manifest.plugin_id:
        raise RuntimeError(
            "health()-Plugin-ID stimmt nicht mit Manifest überein."
        )

    if str(result["version"]) != plugin.manifest.version:
        raise RuntimeError(
            "health()-Version stimmt nicht mit Manifest überein."
        )

    return dict(result)
