from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from mediahub_smart_renamer_runtime.services.rule_pipeline import order_rules_for_final_name


INVALID_WINDOWS_CHARS = '<>:"/\\|?*'


def _pad_media_number(value: Any) -> str:
    text = str(value or "").strip()
    return text.zfill(2) if text.isdigit() else text


def _clean_schema_result(value: str) -> str:
    value = re.sub(r"\\s+", " ", value).strip()
    value = re.sub(r"\\(\\s*\\)", "", value).strip()
    value = re.sub(r"\\s*-\\s*(?=-|$)", "", value).strip()
    value = re.sub(r"^\\s*-\\s*", "", value).strip()
    value = re.sub(r"\\s*-\\s*-\\s*", " - ", value).strip()
    return value



def _split_stem_ext(name: str) -> tuple[str, str]:
    p = Path(name)
    return p.stem, p.suffix

def _replace_literal(value: str, old: str, new: str, *, case_sensitive=False, replace_all=True, whole_word=False) -> str:
    if not old:
        return value
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(old)
    if whole_word:
        pattern = rf"(?<!\w){pattern}(?!\w)"
    return re.sub(pattern, new, value, count=0 if replace_all else 1, flags=flags)

def _remove_range(value: str, start: int, length: int | None = None) -> str:
    n=len(value)
    if start < 0:
        start=max(0,n+start)
    start=min(max(start,0),n)
    end=n if length is None or length < 0 else min(n,start+length)
    return value[:start]+value[end:]

def _insert_at(value: str, position: int, text: str) -> str:
    n=len(value)
    if position < 0:
        position=max(0,n+position+1)
    position=min(max(position,0),n)
    return value[:position]+text+value[position:]

def _remove_relative(value: str, needle: str, mode: str, include_match=False, case_sensitive=False) -> str:
    if not needle:
        return value
    hay=value if case_sensitive else value.casefold()
    ndl=needle if case_sensitive else needle.casefold()
    i=hay.find(ndl)
    if i < 0:
        return value
    if mode=="before":
        return value[i+len(needle):] if include_match else value[i:]
    if mode=="after":
        return value[:i] if include_match else value[:i+len(needle)]
    return value

def _normalize_separators(value: str, separators: str="._") -> str:
    for ch in separators:
        value=value.replace(ch," ")
    return re.sub(r"\s+"," ",value).strip()


def _remove_flexible_suffix(value: str, suffix: str, *, case_sensitive: bool = False) -> str:
    """
    Removes a suffix while tolerating spaces around separator characters.

    Examples for requested "-sd":
      -sd
      - sd
       -sd
       - sd
    """
    suffix=str(suffix or "")
    if not suffix:
        return value

    pattern=[]
    for char in suffix:
        if char.isspace():
            pattern.append(r"\s*")
        elif char in "-_.":
            pattern.append(r"\s*" + re.escape(char) + r"\s*")
        else:
            pattern.append(re.escape(char))

    flags=0 if case_sensitive else re.IGNORECASE
    return re.sub("".join(pattern)+r"\s*$","",value,count=1,flags=flags).rstrip()


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
            "staffel": _pad_media_number((metadata or {}).get("staffel")),
            "episode": _pad_media_number((metadata or {}).get("episode")),
            "episode_bis": _pad_media_number((metadata or {}).get("episode_bis") or (metadata or {}).get("episode_end")),
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

        ordered_rules = order_rules_for_final_name(rules)

        for position, rule in enumerate(ordered_rules):
            if not isinstance(rule, dict) or rule.get("enabled", True) is False:
                continue
            allowed_media_types = [
                str(value).strip().casefold()
                for value in (rule.get("media_types") or [])
                if str(value).strip()
            ]
            current_media_type = str(
                (metadata or {}).get("medientyp")
                or (metadata or {}).get("media_type")
                or ""
            ).strip().casefold()
            if allowed_media_types and "all" not in allowed_media_types and current_media_type not in allowed_media_types:
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
            elif kind == "remove_range":
                user_position = int(rule.get("position") or 1)
                engine_position = user_position - 1 if user_position > 0 else user_position
                result = _remove_range(
                    result,
                    engine_position,
                    int(rule.get("length")) if rule.get("length") not in (None,"") else None,
                )
            elif kind == "remove_start":
                amount = rule.get("count")
                if amount in (None, "", 0, "0"):
                    amount = rule.get("length")
                count=max(0,int(amount or 0))
                result = result[count:]
            elif kind == "remove_end":
                amount = rule.get("count")
                if amount in (None, "", 0, "0"):
                    amount = rule.get("length")
                count=max(0,int(amount or 0))
                result = result[:-count] if count else result
            elif kind == "insert_at":
                user_position = int(rule.get("position") or 1)
                engine_position = user_position - 1 if user_position > 0 else user_position
                result = _insert_at(
                    result,
                    engine_position,
                    str(rule.get("value") or ""),
                )
            elif kind == "replace_advanced":
                result = _replace_literal(result, str(rule.get("old") or ""), str(rule.get("new") or ""),
                    case_sensitive=bool(rule.get("case_sensitive")),
                    replace_all=bool(rule.get("replace_all",True)),
                    whole_word=bool(rule.get("whole_word")))
            elif kind == "regex_replace":
                try:
                    result = re.sub(str(rule.get("pattern") or ""), str(rule.get("replacement") or ""), result,
                                    count=0 if rule.get("replace_all",True) else 1,
                                    flags=0 if rule.get("case_sensitive") else re.IGNORECASE)
                except re.error:
                    pass
            elif kind == "remove_before_extension":
                value = str(rule.get("value") or rule.get("old") or "")
                if value:
                    result = _remove_flexible_suffix(
                        result,
                        value,
                        case_sensitive=bool(rule.get("case_sensitive")),
                    )
            elif kind == "remove_count_before_marker":
                marker = str(rule.get("needle") or "")
                count = max(0, int(rule.get("count") or 0))
                full_name = result + extension
                hay = full_name if rule.get("case_sensitive") else full_name.casefold()
                needle = marker if rule.get("case_sensitive") else marker.casefold()
                marker_pos = hay.find(needle) if needle else -1
                if marker_pos >= 0 and count > 0:
                    start = max(0, marker_pos - count)
                    full_name = full_name[:start] + full_name[marker_pos:]
                    if extension and full_name.endswith(extension):
                        result = full_name[:-len(extension)]
                    else:
                        result = full_name
            elif kind == "remove_relative":
                marker = str(rule.get("needle") or "")
                # Relative markers may include the protected extension, e.g. ".mkv".
                full_name = result + extension
                changed = _remove_relative(
                    full_name,
                    marker,
                    str(rule.get("relative_mode") or "before"),
                    include_match=bool(rule.get("include_match")),
                    case_sensitive=bool(rule.get("case_sensitive")),
                )
                if extension and changed.endswith(extension):
                    result = changed[:-len(extension)]
                else:
                    # Keep the engine's extension-protection contract.
                    result = changed
            elif kind == "normalize_separators":
                result = _normalize_separators(result, str(rule.get("separators") or "._"))
            elif kind == "schema":
                template = str(rule.get("template") or "[original]")
                local = dict(context)
                local["titel"] = str((metadata or {}).get("titel") or result)
                local["original"] = result
                local["nummer"] = str(item_index + 1)
                result = template
                for key, value in local.items():
                    result = result.replace(f"[{key}]", value)
                result = _clean_schema_result(result)

            if result != before:
                applied.append(str(rule.get("label") or kind or f"Regel {position + 1}"))

        protect_extension = not any(
            isinstance(rule, dict)
            and str(rule.get("type") or "").casefold() == "extension"
            and rule.get("protect", True) is False
            for rule in ordered_rules
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
