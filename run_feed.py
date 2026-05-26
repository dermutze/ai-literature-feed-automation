from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from scripts.config_loader import load_config
from scripts.fetch_sources import fetch_all
from scripts.rank_and_export import export_outputs, process_records


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the literature feed locally.")
    parser.add_argument("--config", default=str(ROOT / "config" / "interests.yaml"), help="Path to interests YAML file.")
    parser.add_argument("--root", default=str(ROOT), help="Project root where data/ outputs are written.")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama for optional LLM enrichment.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = load_config(args.config)
    raw = fetch_all(config)
    processed = process_records(raw, config, use_ollama=args.ollama)
    result = export_outputs(processed, Path(args.root))

    print({"raw_count": len(raw), "processed_count": len(processed), "outputs": result})


if __name__ == "__main__":
    main()
