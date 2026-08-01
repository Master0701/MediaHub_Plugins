from __future__ import annotations

import hashlib
import json
import re
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ControlledSourceScanner:
    """Kontrolliertes Laden und strukturierte Vorschau öffentlicher Webseiten."""

    USER_AGENT = "MediaHubSourceScanner/2.6.1"
    MAX_BYTES = 2_000_000
    TIMEOUT_SECONDS = 15

    def __init__(self, cache_path: str | Path):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_url(url: str) -> str:
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Ungültige HTTP- oder HTTPS-URL.")
        return parsed.geturl()

    def _robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def check_policy(self, url: str) -> dict[str, Any]:
        url = self._validate_url(url)
        robots_url = self._robots_url(url)
        request = Request(
            robots_url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "text/plain,*/*;q=0.1",
            },
        )

        result = {
            "url": url,
            "robots_url": robots_url,
            "user_agent": self.USER_AGENT,
            "status": "unknown",
            "allowed": False,
            "http_status": None,
            "content_type": None,
            "robots_found": False,
            "robots_text_preview": None,
            "error_type": None,
            "error": None,
            "requires_manual_confirmation": True,
        }

        try:
            with urlopen(
                request,
                timeout=self.TIMEOUT_SECONDS,
            ) as response:
                result["http_status"] = int(
                    getattr(response, "status", 200) or 200
                )
                result["content_type"] = str(
                    response.headers.get("Content-Type") or ""
                )
                raw = response.read(500_000)
        except HTTPError as exc:
            result["http_status"] = int(exc.code)
            if exc.code == 404:
                result.update(
                    {
                        "status": "robots_missing",
                        "allowed": True,
                        "robots_found": False,
                        "requires_manual_confirmation": False,
                    }
                )
                return result
            result.update(
                {
                    "status": "network_error",
                    "error_type": "http_error",
                    "error": str(exc),
                }
            )
            return result
        except TimeoutError as exc:
            result.update(
                {
                    "status": "timeout",
                    "error_type": "timeout",
                    "error": str(exc),
                }
            )
            return result
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            status = (
                "timeout"
                if isinstance(reason, TimeoutError)
                else "network_error"
            )
            result.update(
                {
                    "status": status,
                    "error_type": type(reason).__name__,
                    "error": str(reason),
                }
            )
            return result
        except Exception as exc:
            result.update(
                {
                    "status": "network_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            return result

        text = raw.decode("utf-8", errors="replace")
        result["robots_found"] = True
        result["robots_text_preview"] = text[:8000]

        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines())

        try:
            allowed = bool(parser.can_fetch(self.USER_AGENT, url))
        except Exception as exc:
            result.update(
                {
                    "status": "unknown",
                    "allowed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "requires_manual_confirmation": True,
                }
            )
            return result

        result["allowed"] = allowed
        result["status"] = "allowed" if allowed else "blocked"
        result["requires_manual_confirmation"] = False
        return result

    @staticmethod
    def _strip_html(html: str) -> str:
        html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
        html = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        text = unescape(text)
        return " ".join(text.split())

    @staticmethod
    def _extract_title(html: str) -> str | None:
        match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
        if not match:
            return None
        return " ".join(unescape(match.group(1)).split())

    @staticmethod
    def _extract_headings(html: str) -> list[str]:
        headings = re.findall(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", html)
        result = []
        for heading in headings[:50]:
            cleaned = ControlledSourceScanner._strip_html(heading)
            if cleaned:
                result.append(cleaned)
        return result

    @staticmethod
    def _extract_links(html: str, base_url: str) -> list[dict[str, str]]:
        links = []
        for href, label in re.findall(
            r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html,
        )[:100]:
            cleaned = ControlledSourceScanner._strip_html(label)
            if cleaned:
                links.append({"href": href, "label": cleaned})
        return links

    def _cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _cache_file(self, url: str) -> Path:
        return self.cache_path / f"{self._cache_key(url)}.json"

    def load_cached(self, url: str) -> dict[str, Any] | None:
        path = self._cache_file(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _save_cache(self, url: str, payload: dict[str, Any]) -> None:
        self._cache_file(url).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def scan(
        self,
        url: str,
        *,
        allow_unknown_policy: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        url = self._validate_url(url)

        if use_cache:
            cached = self.load_cached(url)
            if cached:
                return {**cached, "cache_hit": True}

        policy = self.check_policy(url)
        if policy["status"] == "blocked":
            raise PermissionError(
                "robots.txt untersagt den Zugriff ausdrücklich."
            )
        if policy["status"] in {
            "unknown",
            "network_error",
            "timeout",
        } and not allow_unknown_policy:
            raise PermissionError(
                "Die Zugriffsrichtlinie konnte nicht sicher bestimmt "
                "werden. Bitte die Policy-Diagnose prüfen."
            )

        request = Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(
            request,
            timeout=self.TIMEOUT_SECONDS,
        ) as response:
            content_type = str(response.headers.get("Content-Type") or "")
            raw = response.read(self.MAX_BYTES + 1)

        if len(raw) > self.MAX_BYTES:
            raise ValueError("Die Webseite überschreitet das Größenlimit.")
        if "html" not in content_type.casefold():
            raise ValueError(
                f"Nicht unterstützter Inhaltstyp: {content_type or '-'}"
            )

        html = raw.decode("utf-8", errors="replace")
        text = self._strip_html(html)
        payload = {
            "schema_version": 1,
            "url": url,
            "scanned_at": self._now(),
            "policy": policy,
            "content_type": content_type,
            "byte_count": len(raw),
            "title": self._extract_title(html),
            "headings": self._extract_headings(html),
            "links": self._extract_links(html, url),
            "text_preview": text[:12000],
            "cache_hit": False,
            "automatic_import": False,
            "requires_confirmation": True,
        }
        self._save_cache(url, payload)
        return payload

    def extract_structured_preview(
        self,
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        text = str(scan_result.get("text_preview") or "")
        headings = list(scan_result.get("headings") or [])

        years = sorted(
            {
                int(match)
                for match in re.findall(r"\b(19\d{2}|20\d{2})\b", text)
            }
        )
        season_mentions = re.findall(
            r"(?i)\b(?:staffel|season)\s*(\d{1,3})\b",
            text,
        )
        episode_mentions = re.findall(
            r"(?i)\b(?:folge|episode)\s*(\d{1,4})\b",
            text,
        )
        relation_terms = sorted(
            {
                term
                for term in (
                    "sequel",
                    "prequel",
                    "spin-off",
                    "spinoff",
                    "crossover",
                    "reboot",
                    "remake",
                    "chronologie",
                    "timeline",
                    "franchise",
                    "universum",
                )
                if term in text.casefold()
            }
        )

        return {
            "schema_version": 1,
            "source_url": scan_result.get("url"),
            "source_title": scan_result.get("title"),
            "candidate_headings": headings[:30],
            "years": years[:100],
            "season_mentions": sorted(set(season_mentions)),
            "episode_mentions": sorted(set(episode_mentions)),
            "relation_terms": relation_terms,
            "status": "pending_confirmation",
            "automatic_import": False,
            "requires_confirmation": True,
            "limitations": [
                "Phase 2 extrahiert nur allgemeine Strukturen.",
                "Franchise-spezifische Adapter folgen in späteren Phasen.",
            ],
        }
