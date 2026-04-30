from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
RESULTS_DIR = DATA_DIR / "results"
DOCS_DIR = ROOT / "docs"


def ensure_dirs() -> None:
    for path in (RAW_DIR, INTERMEDIATE_DIR, RESULTS_DIR, DOCS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_openai_api_key(api_key_file: str | Path | None = None) -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    if api_key_file:
        candidate = Path(api_key_file)
        if candidate.exists():
            key = candidate.read_text(encoding="utf-8").strip()
            if key:
                return key

    raise RuntimeError(
        "OpenAI API key was not found. Set OPENAI_API_KEY or pass --api-key-file /path/to/key.txt."
    )
