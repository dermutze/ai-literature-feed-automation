from __future__ import annotations
import os, time, requests, feedparser
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from typing import Dict, Any, List
from scripts.utils import clean_text, normalize_doi, now_iso

USER_AGENT = "local-research-feed-monitor/0.1 (mailto:your_email@example.com)"


def fetch_crossref(keyword: str, rows: int = 10, lookback_days: int = 14) -> List[Dict[str, Any]]:
    from_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date().isoformat()
    url = "https://api.crossref.org/works"
    params = {
        "query": keyword,
        "rows": rows,
        "sort": "published",
        "order": "desc",
        "filter": f"from-pub-date:{from_date}",
    }
    r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    items = r.json().get("message", {}).get("items", [])
    records = []
    for it in items:
        title = clean_text((it.get("title") or [""])[0])
        authors = []
        for a in it.get("author", []) or []:
            authors.append(" ".join([a.get("given", ""), a.get("family", "")]).strip())
        year = ""
        for key in ["published-print", "published-online", "created", "issued"]:
            try:
                year = it[key]["date-parts"][0][0]
                break
            except Exception:
                pass
        records.append({
            "source": "crossref",
            "keyword": keyword,
            "title": title,
            "abstract": clean_text(it.get("abstract", "")),
            "authors": authors,
            "journal": clean_text((it.get("container-title") or [""])[0]),
            "year": year,
            "doi": normalize_doi(it.get("DOI")),
            "url": it.get("URL", ""),
            "published": str(year),
            "fetched_at": now_iso(),
        })
    return records


def fetch_arxiv(keyword: str, rows: int = 10, lookback_days: int = 14) -> List[Dict[str, Any]]:
    # arXiv Atom API. Search by all fields, sort by submitted date.
    query = quote_plus(f'all:"{keyword}"')
    url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={rows}&sortBy=submittedDate&sortOrder=descending"
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    records = []
    for e in feed.entries:
        published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc) if getattr(e, "published_parsed", None) else None
        if published and published < cutoff:
            continue
        doi = normalize_doi(getattr(e, "arxiv_doi", ""))
        authors = [a.name for a in getattr(e, "authors", [])]
        records.append({
            "source": "arxiv",
            "keyword": keyword,
            "title": clean_text(e.title),
            "abstract": clean_text(e.summary),
            "authors": authors,
            "journal": "arXiv",
            "year": published.year if published else "",
            "doi": doi,
            "url": e.link,
            "published": published.isoformat() if published else "",
            "fetched_at": now_iso(),
        })
    time.sleep(3)  # polite arXiv use
    return records


def fetch_semantic_scholar(keyword: str, rows: int = 10, lookback_days: int = 14) -> List[Dict[str, Any]]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    year_from = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).year
    params = {
        "query": keyword,
        "limit": rows,
        "fields": "title,abstract,authors,year,venue,url,externalIds,publicationDate,citationCount",
        "year": f"{year_from}-",
    }
    headers = {"User-Agent": USER_AGENT}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    records = []
    for it in r.json().get("data", []) or []:
        ext = it.get("externalIds") or {}
        records.append({
            "source": "semantic_scholar",
            "keyword": keyword,
            "title": clean_text(it.get("title")),
            "abstract": clean_text(it.get("abstract")),
            "authors": [a.get("name", "") for a in it.get("authors", [])],
            "journal": clean_text(it.get("venue", "")),
            "year": it.get("year", ""),
            "doi": normalize_doi(ext.get("DOI")),
            "url": it.get("url", ""),
            "published": it.get("publicationDate", ""),
            "citation_count": it.get("citationCount", 0),
            "fetched_at": now_iso(),
        })
    return records


def fetch_all(config: dict) -> list[dict]:
    rows = int(config.get("max_results_per_keyword", 10))
    lookback = int(config.get("lookback_days", 14))
    sources = config.get("sources", {})
    out = []
    for kw in config.get("keywords", []):
        if sources.get("crossref", True):
            try: out.extend(fetch_crossref(kw, rows, lookback))
            except Exception as e: out.append({"source":"crossref", "keyword":kw, "error":str(e), "fetched_at":now_iso()})
        if sources.get("arxiv", True):
            try: out.extend(fetch_arxiv(kw, rows, lookback))
            except Exception as e: out.append({"source":"arxiv", "keyword":kw, "error":str(e), "fetched_at":now_iso()})
        if sources.get("semantic_scholar", True):
            try: out.extend(fetch_semantic_scholar(kw, rows, lookback))
            except Exception as e: out.append({"source":"semantic_scholar", "keyword":kw, "error":str(e), "fetched_at":now_iso()})
    return out
