from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOTS = (
    ("MediaHub", ROOT / "plugins"),
    ("AI-Node", ROOT / "ai_node_plugins"),
)


@dataclass(frozen=True)
class SuiteResult:
    group: str
    plugin_name: str
    summary: str
    duration: float
    success: bool
    output: str


def discover_plugin_test_suites() -> list[tuple[str, Path]]:
    suites: list[tuple[str, Path]] = []

    for group, plugin_root in PLUGIN_ROOTS:
        if not plugin_root.exists():
            continue
        for tests_dir in sorted(plugin_root.glob("*/tests")):
            if any(tests_dir.glob("test_*.py")):
                suites.append((group, tests_dir))

    return suites


def _extract_summary(output: str) -> str:
    summary_lines = [
        line.strip()
        for line in output.splitlines()
        if " passed" in line
        or " failed" in line
        or " error" in line
        or " skipped" in line
    ]
    return summary_lines[-1] if summary_lines else "Ergebnis unbekannt"


def run_plugin_suite(group: str, tests_dir: Path) -> SuiteResult:
    plugin_root = tests_dir.parent
    env = os.environ.copy()

    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(plugin_root)
        if not existing_pythonpath
        else str(plugin_root) + os.pathsep + existing_pythonpath
    )

    started = time.perf_counter()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-q",
            "--import-mode=prepend",
        ],
        cwd=plugin_root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    duration = time.perf_counter() - started

    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    )

    return SuiteResult(
        group=group,
        plugin_name=plugin_root.name,
        summary=_extract_summary(output),
        duration=duration,
        success=completed.returncode == 0,
        output=output,
    )


def run_all_plugin_suites(
    *,
    print_output: bool = True,
) -> list[SuiteResult]:
    suites = discover_plugin_test_suites()

    if print_output:
        print("")
        print("=" * 72)
        print("MediaHub Plugin-Gesamttest")
        print("=" * 72)

    if not suites:
        if print_output:
            print("Keine Plugin-Testsuiten vorhanden.")
        return []

    results: list[SuiteResult] = []

    for group, tests_dir in suites:
        plugin_name = tests_dir.parent.name

        if print_output:
            print(
                f"[TEST] [{group}] {plugin_name} ...",
                flush=True,
            )

        result = run_plugin_suite(group, tests_dir)
        results.append(result)

        if print_output:
            state = "OK" if result.success else "FEHLER"
            print(
                f"[{state}] [{result.group}] {result.plugin_name}: "
                f"{result.summary} ({result.duration:.2f} s)"
            )

    if print_output:
        successful = sum(result.success for result in results)
        failed = len(results) - successful
        total_duration = sum(result.duration for result in results)

        print("-" * 72)
        print(
            f"Zusammenfassung: {successful} erfolgreich, "
            f"{failed} fehlgeschlagen, "
            f"{len(results)} Plugin-Suiten"
        )
        print(
            f"Gesamtlaufzeit der Plugin-Suiten: "
            f"{total_duration:.2f} s"
        )
        print("=" * 72)

    return results


def format_failures(results: list[SuiteResult]) -> str:
    details: list[str] = []

    for result in results:
        if result.success:
            continue

        details.append(
            "\n".join(
                [
                    "",
                    "#" * 72,
                    f"FEHLER: [{result.group}] {result.plugin_name}",
                    "#" * 72,
                    result.output or "Keine Testausgabe vorhanden.",
                ]
            )
        )

    return "\n".join(details)


def main() -> int:
    results = run_all_plugin_suites(print_output=True)
    failures = [result for result in results if not result.success]

    if failures:
        print(format_failures(results), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
