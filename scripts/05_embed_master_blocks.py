from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import load_openai_api_key, read_json, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI embeddings for extracted request or mention blocks in the normalized master JSON."
    )
    parser.add_argument("--input", required=True, help="Input master JSON written by 03_parse_llm_blocks.py")
    parser.add_argument("--output", required=True, help="Output JSONL path for block embeddings.")
    parser.add_argument("--model", default="text-embedding-3-large", help="Embedding model name.")
    parser.add_argument("--sleep-seconds", type=float, default=0.5, help="Delay between API calls to reduce request bursts.")
    parser.add_argument("--label-filter", default="Yes", help="Only rows whose label matches this value are embedded.")
    parser.add_argument("--api-key-file", default=None, help="Optional text file containing an OpenAI API key.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_json(Path(args.input))
    client = None if args.dry_run else OpenAI(api_key=load_openai_api_key(args.api_key_file))
    out_rows = []
    for row in rows:
        if row.get("label") != args.label_filter or not row.get("content"):
            continue
        if args.dry_run:
            embedding = []
        else:
            response = client.embeddings.create(model=args.model, input=row["content"])
            embedding = response.data[0].embedding
            time.sleep(args.sleep_seconds)
        out_rows.append({
            "id": str(row["content_id"]),
            "statement_id": row["statement_id"],
            "meeting_id": row.get("meeting_id", ""),
            "text": row["content"],
            "embedding": embedding,
        })

    write_jsonl(Path(args.output), out_rows)


if __name__ == "__main__":
    main()
