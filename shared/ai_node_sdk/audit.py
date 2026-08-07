from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .compatibility import check_manifest_compatibility
from .loader import load_plugin, read_health
from .manifest import load_manifest


@dataclass(frozen=True, slots=True)
class AuditIssue:
    level: str
    plugin_id: str
    message: str


@dataclass(frozen=True, slots=True)
class AuditReport:
    checked_plugins: int
    issues: tuple[AuditIssue, ...]

    @property
    def ok(self) -> bool:
        return not any(
            issue.level == "error"
            for issue in self.issues
        )


def audit_ai_node_plugins(
    plugin_root: str | Path,
) -> AuditReport:
    root = Path(plugin_root)
    issues: list[AuditIssue] = []
    seen_ids: set[str] = set()
    checked = 0

    if not root.exists():
        return AuditReport(
            checked_plugins=0,
            issues=(
                AuditIssue(
                    level="error",
                    plugin_id="",
                    message=f"Plugin-Verzeichnis fehlt: {root}",
                ),
            ),
        )

    for manifest_path in sorted(root.glob("*/plugin.json")):
        checked += 1

        try:
            manifest = load_manifest(manifest_path)
        except Exception as exc:
            issues.append(
                AuditIssue(
                    level="error",
                    plugin_id="",
                    message=(
                        f"{manifest_path}: Manifestfehler: {exc}"
                    ),
                )
            )
            continue

        if manifest.plugin_id in seen_ids:
            issues.append(
                AuditIssue(
                    level="error",
                    plugin_id=manifest.plugin_id,
                    message="Doppelte Plugin-ID.",
                )
            )
            continue
        seen_ids.add(manifest.plugin_id)

        compatibility = check_manifest_compatibility(
            manifest
        )
        if not compatibility.compatible:
            issues.append(
                AuditIssue(
                    level="error",
                    plugin_id=manifest.plugin_id,
                    message=compatibility.reason,
                )
            )
            continue

        try:
            loaded = load_plugin(manifest_path)
        except Exception as exc:
            issues.append(
                AuditIssue(
                    level="error",
                    plugin_id=manifest.plugin_id,
                    message=f"Plugin konnte nicht geladen werden: {exc}",
                )
            )
            continue

        if "health_check" in manifest.capability_names:
            try:
                read_health(loaded)
            except Exception as exc:
                issues.append(
                    AuditIssue(
                        level="error",
                        plugin_id=manifest.plugin_id,
                        message=f"Health-Vertrag ungültig: {exc}",
                    )
                )

        if not manifest.capability_names:
            issues.append(
                AuditIssue(
                    level="warning",
                    plugin_id=manifest.plugin_id,
                    message="Plugin meldet keine Capabilities.",
                )
            )

    return AuditReport(
        checked_plugins=checked,
        issues=tuple(issues),
    )
