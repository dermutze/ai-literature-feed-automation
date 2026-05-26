from __future__ import annotations
import re, json, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Iterable

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    m = DOI_RE.search(doi)
    return m.group(0).rstrip(".,);]").lower() if m else doi.strip().lower()


def make_id(record: Dict[str, Any]) -> str:
    doi = normalize_doi(record.get("doi"))
    if doi:
        return doi.replace("/", "_").replace(":", "_")
    raw = (record.get("title", "") + record.get("url", "")).lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def load_jsonl(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def append_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
