from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import load_openai_api_key, write_jsonl


def iter_html_paragraphs(path: Path, stage: str):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for paragraph in soup.find_all("p"):
        pid = paragraph.get("id")
        if not pid:
            continue
        text = paragraph.get_text(strip=True)
        if not text:
            continue
        yield {
            "id": pid,
            "text": text,
            "stage": stage,
            "source_html": path.name,
        }


def iter_json_paragraphs(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    stage = payload.get("document_type", "unknown")
    for paragraph in payload.get("paragraphs", []):
        yield {
            "id": paragraph["id"],
            "text": paragraph["text"],
            "stage": stage,
            "source_html": paragraph.get("source_html", path.name),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI embeddings for paragraph-level policy document data from HTML or normalized JSON."
    )
    parser.add_argument("--input", required=True, help="Input HTML or JSON file.")
    parser.add_argument("--input-type", choices=("html", "json"), required=True, help="Choose 'html' for raw policy HTML or 'json' for normalized paragraph JSON.")
    parser.add_argument("--stage", required=True, help="Document stage label, for example: initial_draft, draft, final_draft")
    parser.add_argument("--output", required=True, help="Output JSONL path for paragraph embeddings.")
    parser.add_argument("--model", default="text-embedding-3-large", help="Embedding model name.")
    parser.add_argument("--sleep-seconds", type=float, default=0.5, help="Delay between API calls to reduce request bursts.")
    parser.add_argument("--api-key-file", default=None, help="Optional text file containing an OpenAI API key.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = Path(args.input)
    rows = iter_html_paragraphs(path, args.stage) if args.input_type == "html" else iter_json_paragraphs(path)
    client = None if args.dry_run else OpenAI(api_key=load_openai_api_key(args.api_key_file))

    output_rows = []
    for row in rows:
        if args.dry_run:
            embedding = []
        else:
            response = client.embeddings.create(model=args.model, input=row["text"])
            embedding = response.data[0].embedding
            time.sleep(args.sleep_seconds)
        output_rows.append({
            "id": row["id"],
            "text": row["text"],
            "stage": row["stage"],
            "source_html": row["source_html"],
            "embedding": embedding,
        })

    write_jsonl(Path(args.output), output_rows)


if __name__ == "__main__":
    main()
