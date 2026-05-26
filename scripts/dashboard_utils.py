from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value)


def latest_file(directory: Path, pattern: str) -> Optional[Path]:
    if not directory.exists():
        return None
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def list_files(directory: Path, pattern: str) -> List[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)


def normalize_papers(df: pd.DataFrame) -> pd.DataFrame:
    expected_defaults: Dict[str, Any] = {
        "id": "",
        "title": "",
        "abstract": "",
        "authors": [],
        "journal": "",
        "year": "",
        "doi": "",
        "url": "",
        "source": "",
        "keyword": "",
        "relevance_score": 0,
        "rule_score": 0,
        "battery_relevance": "",
        "sioc_pdc_relevance": "",
        "hard_carbon_relevance": "",
        "action": "",
        "confidence": "",
        "reason": "",
        "summary": "",
        "topics": [],
        "published": "",
        "fetched_at": "",
        "keep": True,
        "bibtex": "",
    }
    for column, default in expected_defaults.items():
        if column not in df.columns:
            if isinstance(default, list):
                df[column] = [list(default) for _ in range(len(df))]
            else:
                df[column] = default

    list_like_columns = {"authors", "topics", "summary"}
    for column in df.columns:
        if column not in list_like_columns:
            df[column] = df[column].apply(safe_text)

    df["authors_display"] = df["authors"].apply(safe_text)
    df["topics_display"] = df["topics"].apply(safe_text) if "topics" in df else ""
    df["year"] = df["year"].apply(lambda x: str(x).strip() if safe_text(x) else "")
    df["score_numeric"] = pd.to_numeric(df["relevance_score"], errors="coerce").fillna(0).astype(int)
    df["has_doi"] = df["doi"].apply(lambda x: bool(safe_text(x)))

    def _dedupe_key(row: pd.Series) -> str:
        doi = safe_text(row.get("doi")).lower().strip()
        if doi:
            return f"doi::{doi}"
        return "title::" + safe_text(row.get("title")).lower().strip()

    df["_dedupe_key"] = df.apply(_dedupe_key, axis=1)
    df = df.drop_duplicates(subset=["_dedupe_key"], keep="last").drop(columns=["_dedupe_key"])
    return df.reset_index(drop=True)


def load_jsonl(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)

    if not rows:
        return pd.DataFrame()
    return normalize_papers(pd.DataFrame(rows))


def papers_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "No papers selected."
    lines = ["| # | Title | Year | Journal | Score | DOI |", "|---:|---|---:|---|---:|---|"]
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        title = safe_text(row.get("title")).replace("|", "\\|")
        journal = safe_text(row.get("journal")).replace("|", "\\|")
        lines.append(
            f"| {i} | {title} | {safe_text(row.get('year'))} | {journal} | "
            f"{safe_text(row.get('relevance_score'))} | {safe_text(row.get('doi'))} |"
        )
    return "\n".join(lines) + "\n"


def papers_to_bibtex(df: pd.DataFrame) -> str:
    bibs = [safe_text(x) for x in df.get("bibtex", pd.Series(dtype=str)).tolist() if safe_text(x)]
    if bibs:
        return "\n\n".join(bibs) + "\n"

    from scripts.rank_and_export import make_bibtex

    return "\n\n".join(make_bibtex(row.to_dict()) for _, row in df.iterrows()) + "\n"


def papers_to_ris(df: pd.DataFrame) -> str:
    from scripts.rank_and_export import make_ris

    return "\n\n".join(make_ris(row.to_dict()) for _, row in df.iterrows()) + "\n"


def build_llm_context(df: pd.DataFrame, max_papers: int = 12) -> str:
    if df.empty:
        return "No papers available."
    blocks: List[str] = []
    for i, (_, row) in enumerate(df.head(max_papers).iterrows(), start=1):
        blocks.append(
            f"Paper {i}\n"
            f"Title: {safe_text(row.get('title'))}\n"
            f"Authors: {safe_text(row.get('authors'))}\n"
            f"Journal: {safe_text(row.get('journal'))}\n"
            f"Year: {safe_text(row.get('year'))}\n"
            f"DOI: {safe_text(row.get('doi'))}\n"
            f"Score: {safe_text(row.get('relevance_score'))}\n"
            f"Action: {safe_text(row.get('action'))}\n"
            f"Ranking reason: {safe_text(row.get('reason'))}\n"
            f"Abstract: {safe_text(row.get('abstract'))[:1800]}"
        )
    return "\n\n".join(blocks)
