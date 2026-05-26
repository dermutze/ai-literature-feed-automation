from __future__ import annotations

import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, Any, List

from scripts.utils import make_id, append_jsonl, now_iso


# -----------------------------------------------------------------------------
# Core relevance vocabulary
# -----------------------------------------------------------------------------
# These terms define your actual scientific scope. A paper must usually contain
# at least one core material term AND one battery/electrochemistry context term
# to be treated as a strong hit.

CORE_MATERIAL_TERMS = [
    "sioc",
    "silicon oxycarbide",
    "polymer derived ceramic",
    "polymer-derived ceramic",
    "pdc",
    "preceramic polymer",
    "hard carbon",
    "carbon anode",
    "anode material",
]

SIOC_PDC_TERMS = [
    "sioc",
    "silicon oxycarbide",
    "polymer derived ceramic",
    "polymer-derived ceramic",
    "pdc",
    "preceramic polymer",
    "ceramization",
    "pyrolysis",
    "free carbon",
    "carbon phase",
]

HARD_CARBON_TERMS = [
    "hard carbon",
    "biomass derived hard carbon",
    "biomass-derived hard carbon",
    "coal-derived hard carbon",
    "carbon anode",
]

BATTERY_CONTEXT_TERMS = [
    "battery",
    "batteries",
    "lithium ion",
    "lithium-ion",
    "li-ion",
    "sodium ion",
    "sodium-ion",
    "na-ion",
    "lithium storage",
    "sodium storage",
    "electrochemical",
    "capacity",
    "specific capacity",
    "reversible capacity",
    "cycling",
    "cycle stability",
    "cycling stability",
    "cycling performance",
    "rate capability",
    "coulombic efficiency",
    "sei",
    "solid electrolyte interphase",
    "charge transfer",
    "ion diffusion",
]

DIRECT_ANODE_TERMS = [
    "anode",
    "anodes",
    "anode material",
    "anode materials",
    "electrode",
    "electrodes",
]

INDIRECT_MATERIAL_TERMS = [
    "electrical conductivity",
    "thermal conductivity",
    "mxene",
    "ceramic composite",
    "ceramic matrix",
    "additive manufacturing",
    "3d printing",
    "mechanical properties",
    "microstructure",
    "phase evolution",
]

# Strong false-positive domains. If these occur without a strong battery/material
# context, they should be removed.
NEGATIVE_TERMS = [
    "tourism",
    "economic",
    "economics",
    "finance",
    "earnings",
    "inventory model",
    "carbon refunds",
    "geothermal",
    "carbon sequestration",
    "co2 hydrate",
    "combustion",
    "methane combustion",
    "coal spontaneous combustion",
    "lithium chloride",
    "clinical",
    "candida",
    "fluconazole",
    "listeriosis",
    "animal-derived products",
    "deaf",
    "hard-of-hearing",
    "hearing students",
    "fuel cell",
    "corrosion",
    "marine",
    "bone",
    "biomedical",
    "fault estimation",
    "energy management",
    "thermite",
    "gasification",
    "microbial",
    "microbiologically",
    "sacrificial anode",
    "road condition",
    "sensor fault",
    "catalyst support",
    "magnetic heating",
    "hydrogenation",
    "dehydrogenation",
    "h2s oxidation",
    "butadiene conversion",
]

# Some terms look relevant but are dangerous alone. They should not boost a paper
# unless paired with real battery/material terms.
WEAK_AMBIGUOUS_TERMS = [
    "carbon",
    "sodium",
    "lithium",
    "hard",
    "performance",
    "storage",
    "derived",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _text(record: Dict[str, Any]) -> str:
    return " ".join([
        str(record.get("title", "")),
        str(record.get("abstract", "")),
        str(record.get("journal", "")),
        str(record.get("keyword", "")),
    ]).lower()


def _count_matches(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term.lower() in text)


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _is_review(text: str) -> bool:
    return (
        "review" in text
        or "perspective" in text
        or "overview" in text
        or "progress" in text
    )


# -----------------------------------------------------------------------------
# Rule-based classification
# -----------------------------------------------------------------------------

def classify_relevance(record: Dict[str, Any]) -> Dict[str, Any]:
    text = _text(record)

    core_hits = _count_matches(text, CORE_MATERIAL_TERMS)
    battery_hits = _count_matches(text, BATTERY_CONTEXT_TERMS)
    anode_hits = _count_matches(text, DIRECT_ANODE_TERMS)
    sioc_hits = _count_matches(text, SIOC_PDC_TERMS)
    hard_carbon_hits = _count_matches(text, HARD_CARBON_TERMS)
    indirect_hits = _count_matches(text, INDIRECT_MATERIAL_TERMS)
    negative_hits = _count_matches(text, NEGATIVE_TERMS)
    weak_hits = _count_matches(text, WEAK_AMBIGUOUS_TERMS)
    is_review = _is_review(text)

    has_core_material = core_hits > 0
    has_battery_context = battery_hits > 0 or anode_hits > 0
    has_direct_battery_material = has_core_material and has_battery_context
    has_sioc_or_pdc = sioc_hits > 0
    has_hard_carbon = hard_carbon_hits > 0

    # Guardrail: if a record has strong negative-domain wording and no real
    # material+battery connection, it should be ignored regardless of weak words.
    if negative_hits > 0 and not has_direct_battery_material:
        return {
            "battery_relevance": "Low",
            "sioc_pdc_relevance": "Low",
            "hard_carbon_relevance": "Low",
            "action": "Ignore",
            "confidence": "High",
            "core_hits": core_hits,
            "battery_hits": battery_hits,
            "anode_hits": anode_hits,
            "sioc_hits": sioc_hits,
            "hard_carbon_hits": hard_carbon_hits,
            "indirect_hits": indirect_hits,
            "negative_hits": negative_hits,
            "weak_hits": weak_hits,
            "is_review": is_review,
        }

    # Battery relevance
    if has_direct_battery_material and (battery_hits >= 2 or anode_hits >= 1):
        battery_relevance = "High"
    elif has_direct_battery_material:
        battery_relevance = "Medium"
    elif has_sioc_or_pdc and indirect_hits >= 1:
        battery_relevance = "Medium"
    else:
        battery_relevance = "Low"

    # SiOC/PDC relevance
    if sioc_hits >= 2:
        sioc_pdc_relevance = "High"
    elif sioc_hits == 1:
        sioc_pdc_relevance = "Medium"
    else:
        sioc_pdc_relevance = "Low"

    # Hard carbon relevance
    if hard_carbon_hits >= 1 and has_battery_context:
        hard_carbon_relevance = "High"
    elif hard_carbon_hits >= 1:
        hard_carbon_relevance = "Medium"
    else:
        hard_carbon_relevance = "Low"

    # Action logic
    if battery_relevance == "High" and (has_hard_carbon or has_sioc_or_pdc):
        action = "Read now"
        confidence = "High"
    elif battery_relevance == "Medium" and (has_hard_carbon or has_sioc_or_pdc):
        action = "Read soon"
        confidence = "Medium"
    elif has_sioc_or_pdc or has_hard_carbon:
        action = "Save"
        confidence = "Medium"
    else:
        action = "Ignore"
        confidence = "High"

    # Reviews are useful, but not urgent unless they are very directly aligned.
    if is_review and action == "Read now":
        action = "Read soon"
        confidence = "Medium"

    return {
        "battery_relevance": battery_relevance,
        "sioc_pdc_relevance": sioc_pdc_relevance,
        "hard_carbon_relevance": hard_carbon_relevance,
        "action": action,
        "confidence": confidence,
        "core_hits": core_hits,
        "battery_hits": battery_hits,
        "anode_hits": anode_hits,
        "sioc_hits": sioc_hits,
        "hard_carbon_hits": hard_carbon_hits,
        "indirect_hits": indirect_hits,
        "negative_hits": negative_hits,
        "weak_hits": weak_hits,
        "is_review": is_review,
    }


def keyword_score(record: Dict[str, Any], config: dict) -> int:
    """Compute a conservative relevance score.

    Design goals:
    - Avoid score saturation; not every good paper should be 100.
    - Eliminate false positives caused by generic words like carbon/sodium/hard.
    - Give high scores to direct battery-anode papers involving SiOC/PDC or hard carbon.
    """
    text = _text(record)
    rel = classify_relevance(record)

    # Immediate reject for clear false-positive domains.
    if rel["action"] == "Ignore" and rel["negative_hits"] > 0:
        return 0

    score = 0

    # Strong core contributions
    score += min(rel["core_hits"], 3) * 12
    score += min(rel["battery_hits"], 4) * 8
    score += min(rel["anode_hits"], 2) * 10
    score += min(rel["sioc_hits"], 3) * 9
    score += min(rel["hard_carbon_hits"], 2) * 12

    # Indirect material relevance helps but should not dominate.
    score += min(rel["indirect_hits"], 3) * 4

    # User keywords help only if the paper already has a real core material term.
    if rel["core_hits"] > 0:
        for kw in config.get("keywords", []):
            kw = str(kw).lower().strip()
            if kw and kw in text:
                score += 5

    for neg in config.get("exclude_keywords", []):
        neg = str(neg).lower().strip()
        if neg and neg in text:
            score -= 45

    # Action-based adjustment
    if rel["action"] == "Read now":
        score += 15
    elif rel["action"] == "Read soon":
        score += 8
    elif rel["action"] == "Save":
        score += 2
    elif rel["action"] == "Ignore":
        score -= 40

    # Review papers are useful, but should not outrank direct experimental papers.
    if rel["is_review"]:
        score -= 8

    # Strong false-positive terms reduce score unless directly relevant.
    if rel["negative_hits"] > 0:
        score -= rel["negative_hits"] * 35

    # Weak ambiguous terms alone should not help. If there is no core material,
    # suppress the score strongly.
    if rel["core_hits"] == 0:
        score -= 50

    # Cap by relevance class to keep ranking meaningful.
    if rel["action"] == "Read now":
        score = min(score, 95)
    elif rel["action"] == "Read soon":
        score = min(score, 78)
    elif rel["action"] == "Save":
        score = min(score, 60)
    else:
        score = min(score, 25)

    return max(0, min(int(score), 100))


# -----------------------------------------------------------------------------
# Optional Ollama enrichment in Python backend
# -----------------------------------------------------------------------------

def ollama_enrich(record: Dict[str, Any], config: dict) -> Dict[str, Any]:
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    desc = config.get("research_description", "")

    prompt = f"""
You are screening scientific papers for a materials scientist.

Research interest:
{desc}

Important rules:
- HIGH battery relevance only if the paper directly studies batteries, anodes, electrochemistry, capacity, cycling, SEI, Li/Na storage, or rate performance.
- MEDIUM battery relevance if the paper studies useful SiOC/PDC/carbon material properties but no direct electrochemical testing.
- LOW battery relevance if it is mainly thermal, mechanical, additive manufacturing, biomedical, economics, combustion, CO2 sequestration, or general non-battery science.
- Do not treat generic words such as carbon, sodium, lithium, hard, or performance as sufficient evidence.

Paper:
Title: {record.get("title", "")}
Journal: {record.get("journal", "")}
Year: {record.get("year", "")}
DOI: {record.get("doi", "")}
Abstract: {record.get("abstract", "")[:4000]}

Return STRICT JSON only:
{{
  "relevance_score": 0,
  "battery_relevance": "High/Medium/Low",
  "sioc_pdc_relevance": "High/Medium/Low",
  "hard_carbon_relevance": "High/Medium/Low",
  "action": "Read now/Read soon/Save/Ignore",
  "reason": "one short sentence",
  "topics": ["topic1", "topic2"],
  "summary": ["bullet 1", "bullet 2", "bullet 3"],
  "keep": true
}}
""".strip()

    try:
        r = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        raw = r.json().get("response", "")
        m = re.search(r"\{.*\}", raw, flags=re.S)
        return json.loads(m.group(0) if m else raw)
    except Exception as e:
        return {"llm_error": str(e)}


# -----------------------------------------------------------------------------
# Dedupe, BibTeX, digest, processing, export
# -----------------------------------------------------------------------------

def dedupe(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []

    for r in records:
        if r.get("error"):
            continue

        rid = make_id(r)

        if rid in seen:
            continue

        seen.add(rid)
        r["id"] = rid
        out.append(r)

    return out


def make_bibtex(record: Dict[str, Any]) -> str:
    title = record.get("title") or "Untitled"
    authors = record.get("authors") or []
    clean_authors = [
        a.strip() for a in authors
        if isinstance(a, str) and a.strip()
    ]

    year = record.get("year") or "n.d."
    doi = record.get("doi") or ""
    journal = record.get("journal") or record.get("source") or ""
    url = record.get("url") or ""

    first = clean_authors[0].split()[-1] if clean_authors else "unknown"
    first_word = title.split()[0] if title.split() else "paper"

    key = f"{first}_{year}_{first_word}"
    key = "".join(c for c in key if c.isalnum() or c in "_-")

    return f"""@article{{{key},
  title = {{{title}}},
  author = {{{" and ".join(clean_authors)}}},
  journal = {{{journal}}},
  year = {{{year}}},
  doi = {{{doi}}},
  url = {{{url}}}
}}"""

def make_ris(record: Dict[str, Any]) -> str:
    title = record.get("title") or ""
    authors = record.get("authors") or []
    year = record.get("year") or ""
    journal = record.get("journal") or record.get("source") or ""
    doi = record.get("doi") or ""
    url = record.get("url") or ""

    lines = [
        "TY  - JOUR",
        f"TI  - {title}",
    ]

    for author in authors:
        if author.strip():
            lines.append(f"AU  - {author}")

    if journal:
        lines.append(f"JO  - {journal}")

    if year:
        lines.append(f"PY  - {year}")

    if doi:
        lines.append(f"DO  - {doi}")

    if url:
        lines.append(f"UR  - {url}")

    lines.append("ER  - ")

    return "\n".join(lines)

def build_digest(records: List[Dict[str, Any]], title: str = "Research Feed Digest") -> str:
    lines = [
        f"# {title}",
        "",
        f"Generated: {now_iso()}",
        "",
    ]

    for i, r in enumerate(records, 1):
        lines.append(f"## {i}. {r.get('title', 'Untitled')}")
        lines.append(f"- Score: {r.get('relevance_score', r.get('rule_score', ''))}")
        lines.append(f"- Action: {r.get('action', '')}")
        lines.append(f"- Battery relevance: {r.get('battery_relevance', '')}")
        lines.append(f"- SiOC/PDC relevance: {r.get('sioc_pdc_relevance', '')}")
        lines.append(f"- Hard carbon relevance: {r.get('hard_carbon_relevance', '')}")
        lines.append(f"- Confidence: {r.get('confidence', '')}")
        lines.append(f"- Source: {r.get('source', '')} | Year: {r.get('year', '')} | DOI: {r.get('doi', '')}")
        lines.append(f"- URL: {r.get('url', '')}")

        if r.get("reason"):
            lines.append(f"- Why relevant: {r['reason']}")

        if r.get("summary"):
            if isinstance(r["summary"], list):
                lines.append("- Summary:")
                for s in r["summary"]:
                    lines.append(f"  - {s}")
            else:
                lines.append(f"- Summary: {r['summary']}")

        lines.append("")

    return "\n".join(lines)


def process_records(
    records: List[Dict[str, Any]],
    config: dict,
    use_ollama: bool = False,
) -> List[Dict[str, Any]]:

    records = dedupe(records)
    processed = []
    min_score = int(config.get("min_relevance_score", 70))

    for r in records:
        rule_info = classify_relevance(r)
        r.update(rule_info)

        r["rule_score"] = keyword_score(r, config)

        if use_ollama:
            enrich = ollama_enrich(r, config)
            r.update(enrich)
        else:
            r["relevance_score"] = r["rule_score"]
            r["keep"] = r["rule_score"] >= min_score and r.get("action") != "Ignore"

            if not r.get("reason"):
                r["reason"] = (
                    f"Rule-based match: battery={r.get('battery_relevance')}, "
                    f"SiOC/PDC={r.get('sioc_pdc_relevance')}, "
                    f"hard carbon={r.get('hard_carbon_relevance')}, "
                    f"action={r.get('action')}."
                )

        score = int(r.get("relevance_score") or r.get("rule_score") or 0)
        r["relevance_score"] = score
        r["bibtex"] = make_bibtex(r)

        if score >= min_score and r.get("keep", True) and r.get("action") != "Ignore":
            processed.append(r)

    return sorted(
        processed,
        key=lambda x: x.get("relevance_score", 0),
        reverse=True,
    )


def export_outputs(records: List[Dict[str, Any]], root: str | Path = ".") -> Dict[str, str | int]:
    root = Path(root)
    stamp = now_iso().replace(":", "-")[:19]

    jsonl_path = root / "data" / "feeds" / "papers.jsonl"
    digest_path = root / "data" / "digests" / f"digest_{stamp}.md"
    bib_path = root / "data" / "bibtex" / f"research_feed_{stamp}.bib"
    ris_path = root / "data" / "ris" / f"research_feed_{stamp}.ris"

    append_jsonl(jsonl_path, records)

    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(build_digest(records), encoding="utf-8")

    bib_path.parent.mkdir(parents=True, exist_ok=True)
    bib_path.write_text(
        "\n\n".join(r.get("bibtex", "") for r in records),
        encoding="utf-8",
    )

    ris_path.parent.mkdir(parents=True, exist_ok=True)

    ris_path.write_text(
        "\n\n".join(make_ris(r) for r in records),
        encoding="utf-8",
    )

    return {
        "count": len(records),
        "jsonl": str(jsonl_path),
        "digest": str(digest_path),
        "bibtex": str(bib_path),
        "ris": str(ris_path),
    }
