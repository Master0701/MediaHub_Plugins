from __future__ import annotations

import argparse
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ai_assistant"
DEFAULT_CONFIG = REPO_ROOT / "test_media" / "ai_acceptance_cases.json"

if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


VIDEO_SUFFIXES = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".m4v",
    ".ts",
    ".m2ts",
    ".webm",
    ".wmv",
    ".mpg",
    ".mpeg",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _normal(value: Any) -> str:
    return " ".join(
        _clean(value)
        .casefold()
        .replace(".", " ")
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _build_runtime(
    config: dict[str, Any],
):
    """
    Baut nur die für den Metadaten-Akzeptanztest benötigten
    Komponenten.

    Der Python-Code stammt aus dem aktuellen Entwicklungsrepository.
    Laufzeitbasis, Provider-Konfiguration und Credentials stammen
    dagegen aus der echten MediaHub-Installation.
    """
    from services.rename_review_provider import (
        RenameReviewProvider,
    )
    from services.batch_rename_review_provider import (
        BatchRenameReviewProvider,
    )
    from services.media_analyzer import MediaAnalyzer
    from services.metadata_review_provider import (
        MetadataAIReviewProvider,
    )

    mediahub_root_value = str(
        config.get("mediahub_root") or ""
    ).strip()

    installed_plugin_value = str(
        config.get("installed_plugin_path") or ""
    ).strip()

    if not mediahub_root_value:
        raise RuntimeError(
            "mediahub_root fehlt in der Acceptance-Konfiguration."
        )

    if not installed_plugin_value:
        raise RuntimeError(
            "installed_plugin_path fehlt in der "
            "Acceptance-Konfiguration."
        )

    mediahub_root = Path(
        mediahub_root_value
    ).expanduser().resolve()

    installed_plugin_path = Path(
        installed_plugin_value
    ).expanduser().resolve()

    if not mediahub_root.is_dir():
        raise RuntimeError(
            f"MediaHub-Laufzeitordner fehlt: {mediahub_root}"
        )

    if not installed_plugin_path.is_dir():
        raise RuntimeError(
            "Installierter KI-Assistent fehlt: "
            f"{installed_plugin_path}"
        )

    knowledge_database_path = (
        mediahub_root
        / "config"
        / "knowledge.sqlite3"
    )

    rename_provider = RenameReviewProvider()

    batch_provider = BatchRenameReviewProvider(
        rename_provider
    )

    analyzer = MediaAnalyzer(
        mediahub_base=mediahub_root,
        knowledge_database_path=knowledge_database_path,
        plugin_path=installed_plugin_path,
    )

    metadata_provider = MetadataAIReviewProvider(
        batch_provider,
        analyzer,
    )

    return analyzer, metadata_provider


def _print_runtime_status(analyzer) -> None:
    manager = analyzer.source_manager

    print("Laufzeit:")
    print(
        "  Provider-Konfiguration:",
        manager.config_path,
    )

    print("  Online-Provider:")

    for provider in manager._providers:
        status = dict(
            provider.status() or {}
        )

        credentials = (
            manager.provider_credentials_present(
                str(provider.id)
            )
        )

        credential_present = any(
            bool(value)
            for value in credentials.values()
        )

        print(
            "   ",
            f"{provider.id}:",
            f"enabled={bool(status.get('enabled'))},",
            f"configured={bool(status.get('configured'))},",
            f"credentials={credential_present}",
        )

    print()


def _extract_result(review: dict[str, Any]) -> dict[str, Any]:
    fields = dict(
        review.get("fields")
        or review.get("suggested")
        or review.get("metadata")
        or {}
    )

    result = dict(
        review.get("result")
        or review.get("analysis")
        or {}
    )

    decision = dict(
        review.get("decision")
        or result.get("decision")
        or {}
    )

    confidence = (
        review.get("confidence")
        if review.get("confidence") not in (None, "")
        else decision.get("confidence")
    )

    if confidence in (None, ""):
        confidence = result.get("confidence")

    try:
        confidence_float = float(confidence or 0.0)
    except (TypeError, ValueError):
        confidence_float = 0.0

    if confidence_float > 1.0:
        confidence_float /= 100.0

    title = (
        fields.get("title")
        or fields.get("episode_title")
        or review.get("title")
        or result.get("title")
    )

    media_type = (
        fields.get("media_type")
        or review.get("media_type")
        or result.get("media_type")
    )

    year = (
        fields.get("year")
        or review.get("year")
        or result.get("year")
    )

    return {
        "media_type": media_type,
        "title": title,
        "year": year,
        "confidence": confidence_float,
        "raw": review,
    }


def _matches_title(
    actual: Any,
    expected: Any,
    aliases: list[str],
) -> bool:
    wanted = {
        _normal(expected),
        *{
            _normal(alias)
            for alias in aliases
        },
    }

    wanted.discard("")

    return _normal(actual) in wanted


def _run_case(
    provider,
    case: dict[str, Any],
    dump_dir: Path,
) -> tuple[bool, dict[str, Any]]:
    media_root = Path(
        str(case.get("_media_root") or "")
    ).expanduser()

    media_file = str(
        case.get("file")
        or case.get("path")
        or ""
    ).strip()

    media_path = Path(media_file).expanduser()

    if not media_path.is_absolute():
        if str(media_root):
            media_path = (
                media_root / media_path
            ).resolve()
        else:
            media_path = (
                REPO_ROOT / media_path
            ).resolve()

    if not media_path.is_file():
        return False, {
            "error": f"Datei fehlt: {media_path}"
        }

    started = time.perf_counter()

    payload = {
        "path": str(media_path),
        "item": {
            "path": str(media_path),
            "file_path": str(media_path),
            "filename": media_path.name,
            "title": media_path.stem,
            "_force_analysis": True,
            "_require_in_video": True,
        },
    }

    review = provider.analyze(payload)

    elapsed = time.perf_counter() - started
    actual = _extract_result(dict(review or {}))

    expected = dict(
        case.get("expected") or {}
    )

    errors: list[str] = []

    expected_type = _clean(
        expected.get("media_type")
    )

    if (
        expected_type
        and _normal(actual["media_type"])
        != _normal(expected_type)
    ):
        errors.append(
            "Medientyp: "
            f"{actual['media_type']!r} != "
            f"{expected_type!r}"
        )

    expected_title = _clean(
        expected.get("title")
    )

    aliases = [
        str(item)
        for item in (
            expected.get("aliases") or []
        )
    ]

    if (
        expected_title
        and not _matches_title(
            actual["title"],
            expected_title,
            aliases,
        )
    ):
        errors.append(
            "Titel: "
            f"{actual['title']!r} nicht in "
            f"{[expected_title, *aliases]!r}"
        )

    expected_year = expected.get("year")

    if expected_year not in (None, ""):
        try:
            actual_year = int(
                actual["year"]
            )
        except (TypeError, ValueError):
            actual_year = None

        if actual_year != int(expected_year):
            errors.append(
                "Jahr: "
                f"{actual_year!r} != "
                f"{int(expected_year)!r}"
            )

    minimum_confidence = expected.get(
        "minimum_confidence"
    )

    if minimum_confidence not in (None, ""):
        minimum = float(
            minimum_confidence
        )

        if minimum > 1.0:
            minimum /= 100.0

        if actual["confidence"] < minimum:
            errors.append(
                "Confidence: "
                f"{actual['confidence'] * 100:.1f}% "
                f"< {minimum * 100:.1f}%"
            )

    maximum_confidence = expected.get(
        "maximum_confidence"
    )

    if maximum_confidence not in (None, ""):
        maximum = float(
            maximum_confidence
        )

        if maximum > 1.0:
            maximum /= 100.0

        if actual["confidence"] > maximum:
            errors.append(
                "Confidence: "
                f"{actual['confidence'] * 100:.1f}% "
                f"> {maximum * 100:.1f}%"
            )

    dump_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    dump_path = (
        dump_dir
        / (
            media_path.stem[:80]
            .replace(" ", "_")
            + ".json"
        )
    )

    dump_path.write_text(
        json.dumps(
            actual["raw"],
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return not errors, {
        "path": str(media_path),
        "media_type": actual["media_type"],
        "title": actual["title"],
        "year": actual["year"],
        "confidence": actual["confidence"],
        "elapsed": elapsed,
        "errors": errors,
        "dump": str(dump_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lokaler MediaHub-KI-Medien-Akzeptanztest "
            "ohne Plugin-Build/Installation."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--only",
        default="",
        help=(
            "Nur Fälle ausführen, deren Name "
            "diesen Text enthält."
        ),
    )

    args = parser.parse_args()

    config = _load_json(
        args.config.resolve()
    )

    cases = list(
        config.get("cases") or []
    )

    media_root = str(
        config.get("media_root") or ""
    ).strip()

    root_path = Path(
        media_root
    ).expanduser().resolve()

    if not root_path.is_dir():
        raise RuntimeError(
            f"Testvideo-Ordner fehlt: {root_path}"
        )

    configured_files = {
        str(
            case.get("file")
            or case.get("path")
            or ""
        ).casefold()
        for case in cases
    }

    video_suffixes = {
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".m4v",
        ".ts",
        ".m2ts",
        ".webm",
        ".wmv",
        ".mpg",
        ".mpeg",
    }

    for media_file in sorted(
        root_path.iterdir(),
        key=lambda item: item.name.casefold(),
    ):
        if not media_file.is_file():
            continue

        if media_file.suffix.casefold() not in video_suffixes:
            continue

        if media_file.name.casefold() in configured_files:
            continue

        cases.append(
            {
                "name": f"OBSERVE: {media_file.name}",
                "file": media_file.name,
                "expected": {},
                "_observe_only": True,
            }
        )

    for case in cases:
        case["_media_root"] = media_root

    if args.only:
        wanted = args.only.casefold()
        cases = [
            case
            for case in cases
            if wanted
            in _clean(
                case.get("name")
            ).casefold()
        ]

    if not cases:
        print(
            "Keine Testfälle gefunden."
        )
        return 2

    print(
        "MediaHub KI-Akzeptanztest"
    )
    print(
        "Quelle:",
        PLUGIN_ROOT,
    )
    print()

    analyzer, provider = _build_runtime(
        config
    )

    _print_runtime_status(
        analyzer
    )

    dump_dir = (
        REPO_ROOT
        / "tools"
        / "dev"
        / "acceptance_results"
    )

    passed = 0
    failed = 0

    for index, case in enumerate(
        cases,
        start=1,
    ):
        name = _clean(
            case.get("name")
        ) or f"Fall {index}"

        print(
            f"[{index}/{len(cases)}] {name}"
        )

        try:
            ok, result = _run_case(
                provider,
                case,
                dump_dir,
            )
        except Exception as exc:
            import traceback

            ok = False
            result = {
                "errors": [
                    f"{type(exc).__name__}: {exc}",
                    traceback.format_exc(),
                ]
            }

        observe_only = bool(
            case.get("_observe_only")
        )

        if ok and observe_only:
            print(
                "  OBSERVE | "
                f"{result['media_type']} | "
                f"{result['title']} | "
                f"{result['year']} | "
                f"{result['confidence'] * 100:.1f}% | "
                f"{result['elapsed']:.2f}s"
            )

        elif ok:
            passed += 1
            print(
                "  PASS | "
                f"{result['media_type']} | "
                f"{result['title']} | "
                f"{result['year']} | "
                f"{result['confidence'] * 100:.1f}% | "
                f"{result['elapsed']:.2f}s"
            )
        else:
            failed += 1
            print("  FAIL")

            for error in (
                result.get("errors") or []
            ):
                print(
                    "       ",
                    error,
                )

            if result.get("dump"):
                print(
                    "       Analyse:",
                    result["dump"],
                )

        print()

    observed = sum(
        1
        for case in cases
        if case.get("_observe_only")
    )

    print("=" * 60)
    print(
        f"{passed} bestanden"
    )
    print(
        f"{failed} fehlgeschlagen"
    )
    print(
        f"{observed} beobachtet"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
