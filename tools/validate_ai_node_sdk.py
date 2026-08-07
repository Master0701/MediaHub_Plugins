from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.ai_node_sdk import audit_ai_node_plugins


def main() -> int:
    report = audit_ai_node_plugins(
        ROOT / "ai_node_plugins"
    )

    print("=" * 72)
    print("MediaHub AI-Node SDK Audit")
    print("=" * 72)
    print(
        f"Geprüfte AI-Node-Plugins: "
        f"{report.checked_plugins}"
    )

    if report.issues:
        for issue in report.issues:
            plugin = (
                f" [{issue.plugin_id}]"
                if issue.plugin_id
                else ""
            )
            print(
                f"[{issue.level.upper()}]{plugin} "
                f"{issue.message}"
            )
    else:
        print("[OK] Keine SDK-/Plugin-Probleme gefunden.")

    print("=" * 72)

    if not report.ok:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
