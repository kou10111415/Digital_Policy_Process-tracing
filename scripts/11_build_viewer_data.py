from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_json, write_json


def read_rows(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    return read_json(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert reflection-judgement output into a single viewer data JSON bundle for the static HTML front end."
    )
    parser.add_argument("--judgements", required=True, help="Input judgement file in JSON or JSONL format.")
    parser.add_argument("--output", required=True, help="Output path for viewer data JSON.")
    args = parser.parse_args()

    rows = read_rows(Path(args.judgements))
    payload = {
        "meta": {
            "title": "Digital Policy Process-tracing Viewer",
            "count": len(rows),
        },
        "items": rows,
    }
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
