from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"


@dataclass(frozen=True)
class SuiteResult:
    plugin_name: str
    summary: str
    duration: float
    success: bool
    output: str


def discover_plugin_test_suites() -> list[Path]:
    suites: list[Path] = []

    for tests_dir in sorted(PLUGINS_DIR.glob("*/tests")):
        if any(tests_dir.glob("test_*.py")):
            suites.append(tests_dir)

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


def run_plugin_suite(tests_dir: Path) -> SuiteResult:
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
        plugin_name=plugin_root.name,
        summary=_extract_summary(output),
        duration=duration,
        success=completed.returncode == 0,
        output=output,
    )


def run_all_plugin_suites(*, print_output: bool = True) -> list[SuiteResult]:
    suites = discover_plugin_test_suites()
    if not suites:
        raise RuntimeError("Keine Plugin-Testsuiten gefunden.")

    if print_output:
        print("")
        print("=" * 72)
        print("MediaHub Plugin-Gesamttest")
        print("=" * 72)

    results: list[SuiteResult] = []

    for tests_dir in suites:
        plugin_name = tests_dir.parent.name

        if print_output:
            print(f"[TEST] {plugin_name} ...", flush=True)

        result = run_plugin_suite(tests_dir)
        results.append(result)

        if print_output:
            state = "OK" if result.success else "FEHLER"
            print(
                f"[{state}] {result.plugin_name}: "
                f"{result.summary} ({result.duration:.2f} s)"
            )

    if print_output:
        successful = sum(result.success for result in results)
        failed = len(results) - successful
        total_duration = sum(result.duration for result in results)

        print("-" * 72)
        print(
            f"Zusammenfassung: {successful} erfolgreich, "
            f"{failed} fehlgeschlagen, {len(results)} Plugin-Suiten"
        )
        print(f"Gesamtlaufzeit der Plugin-Suiten: {total_duration:.2f} s")
        print("=" * 72)

    return results


def format_failures(results: list[SuiteResult]) -> str:
    failures = [result for result in results if not result.success]
    details: list[str] = []

    for result in failures:
        details.append(
            "\n".join(
                [
                    "",
                    "#" * 72,
                    f"FEHLER: {result.plugin_name}",
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
