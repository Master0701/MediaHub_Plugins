from __future__ import annotations

import re
from pathlib import Path
from typing import Any


INVALID_WINDOWS_CHARS = '<>:"/\\|?*'


class RenameRuleEngine:
    """Deterministische, reine Vorschau-Regelengine ohne Dateizugriffe."""

    def apply(
        self,
        name: str,
        rules: list[dict[str, Any]],
        *,
        item_index: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(name)
        stem = path.stem
        extension = path.suffix
        result = stem
        applied: list[str] = []
        context = {
            "original": stem,
            "titel": str((metadata or {}).get("titel") or stem),
            "jahr": str((metadata or {}).get("jahr") or ""),
            "staffel": str((metadata or {}).get("staffel") or ""),
            "episode": str((metadata or {}).get("episode") or ""),
            "episode_bis": str((metadata or {}).get("episode_bis") or (metadata or {}).get("episode_end") or ""),
            "episodentitel": str((metadata or {}).get("episodentitel") or ""),
            "edition": str(
                (metadata or {}).get("edition")
                or (metadata or {}).get("fassung")
                or ""
            ),
            "fassung": str(
                (metadata or {}).get("fassung")
                or (metadata or {}).get("edition")
                or ""
            ),
            "medientyp": str(
                (metadata or {}).get("medientyp")
                or (metadata or {}).get("media_type")
                or ""
            ),
            "teil": str((metadata or {}).get("teil") or (metadata or {}).get("part") or ""),
            "part": str((metadata or {}).get("part") or (metadata or {}).get("teil") or ""),
            "extra_type": str((metadata or {}).get("extra_type") or ""),
            "nummer": str(item_index + 1),
            "endung": extension.lstrip("."),
        }

        for position, rule in enumerate(rules):
            if not isinstance(rule, dict) or rule.get("enabled", True) is False:
                continue
            kind = str(rule.get("type") or "").strip().casefold()
            before = result

            if kind == "replace":
                old = str(rule.get("old") or "")
                if old:
                    result = result.replace(old, str(rule.get("new") or ""))
            elif kind == "remove":
                value = str(rule.get("value") or "")
                if value:
                    result = result.replace(value, "")
            elif kind == "prefix":
                result = str(rule.get("value") or "") + result
            elif kind == "suffix":
                result += str(rule.get("value") or "")
            elif kind == "trim":
                result = " ".join(result.split())
            elif kind == "case":
                mode = str(rule.get("mode") or "").casefold()
                if mode == "lower": result = result.lower()
                elif mode == "upper": result = result.upper()
                elif mode == "title": result = result.title()
                elif mode == "sentence": result = result[:1].upper() + result[1:].lower() if result else result
            elif kind == "numbering":
                start = int(rule.get("start", 1))
                step = int(rule.get("step", 1))
                padding = max(1, int(rule.get("padding", 2)))
                number = start + item_index * step
                value = str(number).zfill(padding)
                separator = str(rule.get("separator") or " ")
                placement = str(rule.get("placement") or "prefix").casefold()
                result = f"{result}{separator}{value}" if placement == "suffix" else f"{value}{separator}{result}"
            elif kind == "schema":
                template = str(rule.get("template") or "[original]")
                local = dict(context)
                local["titel"] = str((metadata or {}).get("titel") or result)
                local["original"] = result
                local["nummer"] = str(item_index + 1)
                result = template
                for key, value in local.items():
                    result = result.replace(f"[{key}]", value)
                result = re.sub(r"\s+", " ", result).strip()
                result = re.sub(r"\(\s*\)", "", result).strip()

            if result != before:
                applied.append(str(rule.get("label") or kind or f"Regel {position + 1}"))

        protect_extension = not any(
            isinstance(rule, dict)
            and str(rule.get("type") or "").casefold() == "extension"
            and rule.get("protect", True) is False
            for rule in rules
        )
        proposed = result + extension if protect_extension else result
        warnings: list[str] = []
        invalid = sorted(set(proposed) & set(INVALID_WINDOWS_CHARS))
        if invalid:
            warnings.append("Ungültige Windows-Zeichen: " + " ".join(invalid))
        if not result.strip(): warnings.append("Der neue Dateiname wäre leer.")
        if proposed.endswith((" ", ".")): warnings.append("Windows-Dateinamen dürfen nicht mit Leerzeichen oder Punkt enden.")

        return {
            "proposed_name": proposed,
            "applied_rules": applied,
            "change_source": ", ".join(applied) if applied else "unverändert",
            "warnings": warnings,
            "extension_protected": protect_extension,
        }
