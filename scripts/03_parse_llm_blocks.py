from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json


def clean_raw_response(raw_response: str) -> str:
    if raw_response.startswith("```json"):
        return raw_response.replace("```json", "").replace("```", "").strip()
    return raw_response


def build_rows(log_path: Path, label: str, content_prefix: str) -> list[dict]:
    rows = []
    content_counter = 1
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            parsed = json.loads(clean_raw_response(record.get("raw_response", "")))
            for item in parsed:
                rows.append({
                    "content_id": str(content_counter),
                    "content_key": f"{content_prefix}{content_counter}",
                    "meeting_id": record.get("meeting_id", ""),
                    "statement_id": record.get("発言ID", ""),
                    "speaker": record.get("発言者", ""),
                    "statement_text": record.get("発言原文", ""),
                    "content": item.get("内容", ""),
                    "label": item.get(label + "あり", ""),
                    "other_reference": item.get("他の委員の発言参照", ""),
                    "page_line": item.get("参照されたページ・行", ""),
                    "reason": item.get("理由", ""),
                    "label_type": label,
                })
                content_counter += 1
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert raw LLM extraction logs into a normalized master table stored as JSON. CSV output is optional."
    )
    parser.add_argument("--input", required=True, help="Input JSONL written by 01_extract_meeting_blocks.py")
    parser.add_argument("--label", choices=("要求", "言及"), default="要求", help="How to interpret the extracted label column.")
    parser.add_argument("--content-prefix", default="content-", help="Prefix used when generating content_key values.")
    parser.add_argument("--output-json", required=True, help="Output path for the normalized master JSON.")
    parser.add_argument("--output-csv", default=None, help="Optional CSV export path for spreadsheet-friendly inspection.")
    args = parser.parse_args()

    rows = build_rows(Path(args.input), args.label, args.content_prefix)
    write_json(Path(args.output_json), rows)
    if args.output_csv:
        write_csv(rows, Path(args.output_csv))


if __name__ == "__main__":
    main()
