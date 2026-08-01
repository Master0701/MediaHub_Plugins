from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import re
import unicodedata

def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()
from services.fingerprint_store import FingerprintReferenceStore
from services.visual_knowledge import VisualKnowledgeStore


def _walk_dicts(value: Any, path: str = "analysis"):
    """Durchläuft verschachtelte Analyseobjekte ohne Endlosschleifen."""
    seen: set[int] = set()

    def walk(current: Any, current_path: str):
        if isinstance(current, (dict, list)):
            object_id = id(current)
            if object_id in seen:
                return
            seen.add(object_id)

        if isinstance(current, dict):
            yield current_path, current
            for key, child in current.items():
                child_path = f"{current_path}.{key}"
                yield from walk(child, child_path)
        elif isinstance(current, list):
            for index, child in enumerate(current):
                yield from walk(child, f"{current_path}[{index}]")

    yield from walk(value, path)


def _find_video_fingerprint(analysis: dict[str, Any]) -> tuple[str | None, str | None]:
    """Findet einen Video-Fingerprint auch in Cache- und Orchestrator-Strukturen."""
    preferred_paths = (
        ("in_video", "agents", "fingerprint_agent", "video_fingerprint"),
        ("orchestration", "result", "in_video", "agents", "fingerprint_agent", "video_fingerprint"),
    )

    for path_parts in preferred_paths:
        current: Any = analysis
        valid = True
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                valid = False
                break
            current = current[part]
        if valid and isinstance(current, str) and current.strip():
            return current.strip(), "analysis." + ".".join(path_parts)

    candidates: list[tuple[int, str, str]] = []
    for path, item in _walk_dicts(analysis):
        for key in ("video_fingerprint", "fingerprint"):
            value = item.get(key)
            if not isinstance(value, str):
                continue
            value = value.strip()
            if len(value) < 16:
                continue
            score = 0
            lowered_path = path.casefold()
            if "fingerprint_agent" in lowered_path:
                score += 100
            if "in_video" in lowered_path:
                score += 50
            if key == "video_fingerprint":
                score += 25
            if len(value) == 64:
                score += 10
            candidates.append((score, value, f"{path}.{key}"))

    if not candidates:
        return None, None

    candidates.sort(key=lambda entry: entry[0], reverse=True)
    _, fingerprint, source_path = candidates[0]
    return fingerprint, source_path


class KnowledgeLearningService:
    """Persistiert ausschließlich vom Benutzer bestätigtes Medienwissen."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.fingerprints = FingerprintReferenceStore(self.database_path)
        self.visual_knowledge = VisualKnowledgeStore(self.database_path)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=10.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def ensure_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS ai_learned_identities (
                id INTEGER PRIMARY KEY,
                media_type TEXT NOT NULL,
                canonical_title TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                original_title TEXT,
                release_year INTEGER,
                season INTEGER,
                episode INTEGER,
                edition TEXT,
                external_ids_json TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'user_confirmation',
                confidence REAL NOT NULL DEFAULT 1.0,
                confirmed_by_user INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ai_learned_aliases (
                id INTEGER PRIMARY KEY,
                identity_id INTEGER NOT NULL REFERENCES ai_learned_identities(id) ON DELETE CASCADE,
                alias TEXT NOT NULL,
                normalized_alias TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'user_confirmation',
                confidence REAL NOT NULL DEFAULT 1.0,
                confirmed_by_user INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_alias, identity_id)
            );
            CREATE TABLE IF NOT EXISTS ai_knowledge_conflicts (
                id INTEGER PRIMARY KEY,
                normalized_key TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                existing_value TEXT,
                proposed_value TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_ai_alias_normalized ON ai_learned_aliases(normalized_alias);
            CREATE INDEX IF NOT EXISTS idx_ai_identity_normalized ON ai_learned_identities(normalized_title);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_identity_unique ON ai_learned_identities(normalized_title,media_type,release_year,season,episode);
            """)

    def confirm(self, analysis: dict[str, Any], corrected_identity: dict[str, Any] | None = None) -> dict[str, Any]:
        proposed = dict(corrected_identity or {})
        identification = analysis.get('identification') or {}
        decision = analysis.get('decision') or {}
        title = str(proposed.get('title') or decision.get('title_candidate') or identification.get('title_candidate') or '').strip()
        media_type = str(proposed.get('media_type') or decision.get('media_type') or identification.get('media_type') or 'other').strip().lower()
        if not title:
            raise ValueError('Für das Lernen wird ein bestätigter Titel benötigt.')
        year = proposed.get('year', identification.get('year'))
        season = proposed.get('season', decision.get('season'))
        episodes = proposed.get('episodes', decision.get('episodes') or identification.get('episodes') or [])
        episode = proposed.get('episode')
        if episode is None and episodes: episode = episodes[0]
        edition = proposed.get('edition') or identification.get('edition_candidate')
        original_title = proposed.get('original_title')
        external_ids = proposed.get('external_ids') or {}
        normalized = normalize_text(title)
        source = str(proposed.get('source') or 'user_confirmation')
        confidence = float(proposed.get('confidence', 1.0))
        aliases = {str(x).strip() for x in proposed.get('aliases') or [] if str(x).strip()}
        for candidate in (identification.get('title_candidate'), (analysis.get('file') or {}).get('name')):
            if candidate and normalize_text(str(candidate)) != normalized:
                aliases.add(str(candidate).strip())

        conflicts=[]
        with self._connect() as db:
            for row in db.execute("""SELECT i.id,i.canonical_title,i.media_type FROM ai_learned_aliases a JOIN ai_learned_identities i ON i.id=a.identity_id WHERE a.normalized_alias IN (%s)""" % ','.join('?' for _ in aliases), tuple(normalize_text(a) for a in aliases)).fetchall() if aliases else []:
                if normalize_text(row['canonical_title']) != normalized:
                    conflicts.append({'alias': next((a for a in aliases if normalize_text(a) in {normalize_text(x) for x in aliases}), ''), 'existing_title': row['canonical_title'], 'proposed_title': title})
            db.execute("""INSERT INTO ai_learned_identities(media_type,canonical_title,normalized_title,original_title,release_year,season,episode,edition,external_ids_json,source,confidence)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(normalized_title,media_type,release_year,season,episode) DO UPDATE SET canonical_title=excluded.canonical_title,original_title=COALESCE(excluded.original_title,ai_learned_identities.original_title),edition=COALESCE(excluded.edition,ai_learned_identities.edition),external_ids_json=excluded.external_ids_json,source=excluded.source,confidence=excluded.confidence,updated_at=CURRENT_TIMESTAMP""",
                (media_type,title,normalized,original_title,year,season,episode,edition,json.dumps(external_ids,ensure_ascii=False),source,confidence))
            identity_id=int(db.execute("SELECT id FROM ai_learned_identities WHERE normalized_title=? AND media_type=? AND COALESCE(release_year,-1)=COALESCE(?,-1) AND COALESCE(season,-1)=COALESCE(?,-1) AND COALESCE(episode,-1)=COALESCE(?,-1)",(normalized,media_type,year,season,episode)).fetchone()['id'])
            for alias in sorted(aliases):
                db.execute("INSERT OR IGNORE INTO ai_learned_aliases(identity_id,alias,normalized_alias,source,confidence) VALUES(?,?,?,?,?)",(identity_id,alias,normalize_text(alias),source,confidence))
            for c in conflicts:
                db.execute("INSERT INTO ai_knowledge_conflicts(normalized_key,conflict_type,existing_value,proposed_value,details_json) VALUES(?,?,?,?,?)",(normalize_text(c['alias']),'alias_identity',c['existing_title'],title,json.dumps(c,ensure_ascii=False)))

        fingerprint, fingerprint_source = _find_video_fingerprint(analysis)
        fp_record=None
        if fingerprint:
            source_path = str((analysis.get('file') or {}).get('path') or '')
            if not source_path:
                for nested_path, nested in _walk_dicts(analysis):
                    file_data = nested.get('file')
                    if isinstance(file_data, dict) and file_data.get('path'):
                        source_path = str(file_data.get('path'))
                        break
            fp_record=self.fingerprints.register(
                fingerprint,
                {
                    'media_type':media_type,
                    'title':title,
                    'year':year,
                    'season':season,
                    'episode':episode,
                    'edition':edition,
                    'knowledge_identity_id':identity_id,
                    'confidence':confidence,
                    'source':source,
                },
                source_path or None,
            )
        visual_record = None
        visual = analysis.get('visual_intelligence')
        if not isinstance(visual, dict):
            visual = (analysis.get('in_video') or {}).get('visual_intelligence')
        if not isinstance(visual, dict):
            for nested_path, nested in _walk_dicts(analysis):
                candidate = nested.get('visual_intelligence')
                if isinstance(candidate, dict):
                    visual = candidate
                    break
        if isinstance(visual, dict):
            visual_record = self.visual_knowledge.register_confirmed(
                identity_id,
                visual,
                source=source,
                confidence=confidence,
                confirmed_by_user=True,
            )

        return {
            'schema_version':3,
            'status':'confirmed_and_learned',
            'identity_id':identity_id,
            'identity':{
                'media_type':media_type,
                'title':title,
                'year':year,
                'season':season,
                'episode':episode,
                'edition':edition,
            },
            'aliases':sorted(aliases),
            'fingerprint':fp_record,
            'fingerprint_detected':bool(fingerprint),
            'fingerprint_source':fingerprint_source,
            'visual_knowledge':visual_record,
            'visual_knowledge_detected':bool(visual_record and visual_record.get('persisted')),
            'database_path':str(self.database_path.resolve()),
            'conflicts':conflicts,
            'source':source,
            'confidence':confidence,
        }

    def lookup(self, query: str) -> list[dict[str, Any]]:
        key=normalize_text(query)
        if not key: return []
        with self._connect() as db:
            rows=db.execute("""SELECT DISTINCT i.* FROM ai_learned_identities i LEFT JOIN ai_learned_aliases a ON a.identity_id=i.id WHERE i.normalized_title=? OR a.normalized_alias=? ORDER BY i.confidence DESC""",(key,key)).fetchall()
            result=[]
            for row in rows:
                item=dict(row); item['external_ids']=json.loads(item.pop('external_ids_json') or '{}'); item['aliases']=[x['alias'] for x in db.execute('SELECT alias FROM ai_learned_aliases WHERE identity_id=? ORDER BY alias',(row['id'],)).fetchall()]; result.append(item)
            return result

    def conflicts(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(x) for x in db.execute("SELECT * FROM ai_knowledge_conflicts WHERE status='open' ORDER BY created_at DESC").fetchall()]

    def export_snapshot(self) -> dict[str, Any]:
        with self._connect() as db:
            identities=[dict(x) for x in db.execute('SELECT * FROM ai_learned_identities ORDER BY canonical_title').fetchall()]
            aliases=[dict(x) for x in db.execute('SELECT * FROM ai_learned_aliases ORDER BY alias').fetchall()]
        for item in identities: item['external_ids']=json.loads(item.pop('external_ids_json') or '{}')
        return {'schema_version':1,'producer':'mediahub.ai_assistant.knowledge_learning','supports_media_types':['movie','series','season','episode','special','audiobook','book','other'],'identities':identities,'aliases':aliases,'conflicts':self.conflicts()}
