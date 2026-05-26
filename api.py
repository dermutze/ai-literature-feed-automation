from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from scripts.config_loader import load_config
from scripts.fetch_sources import fetch_all
from scripts.rank_and_export import export_outputs, process_records

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = FastAPI(title="Research Feed Monitor", version="0.2.0")


class FeedRequest(BaseModel):
    config_path: str = "config/interests.yaml"
    use_ollama: bool = False
    max_returned_papers: int = 20


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/run_feed")
def run_feed(req: FeedRequest) -> Dict[str, Any]:
    config_path = Path(req.config_path)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    config = load_config(config_path)
    raw = fetch_all(config)
    processed = process_records(raw, config, use_ollama=req.use_ollama)
    outputs = export_outputs(processed, ROOT)

    return {
        "raw_count": len(raw),
        "processed_count": len(processed),
        "outputs": outputs,
        "papers": processed[: max(0, req.max_returned_papers)],
    }
