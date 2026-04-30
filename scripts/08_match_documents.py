from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json


def collect_matches(source_collection, target_collection, top_n: int, score_threshold: float | None = None) -> list[dict]:
    results = []
    source_rows = source_collection.get(include=["embeddings"])
    for source_id, embedding in zip(source_rows.get("ids", []), source_rows.get("embeddings", [])):
        matches = target_collection.query(query_embeddings=[embedding], n_results=top_n, include=["distances", "documents"])
        for matched_id, score, doc_text in zip(matches["ids"][0], matches["distances"][0], matches.get("documents", [[]])[0]):
            if score_threshold is not None and score is not None and score > score_threshold:
                continue
            results.append({
                "request_id": str(source_id),
                "matched_id": str(matched_id),
                "score": score,
                "text": doc_text,
            })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve paragraph-to-paragraph candidate links between two document stages, for example initial_draft -> draft."
    )
    parser.add_argument("--db-path", required=True, help="Directory used by ChromaDB for persistent storage.")
    parser.add_argument("--source-collection", required=True, help="Collection for the earlier document stage.")
    parser.add_argument("--target-collection", required=True, help="Collection for the later document stage.")
    parser.add_argument("--output", required=True, help="Output JSON path for document-stage candidate links.")
    parser.add_argument("--top-n", type=int, default=20, help="Maximum number of candidates to keep per source paragraph.")
    parser.add_argument("--score-threshold", type=float, default=None, help="Optional cosine-distance cutoff. Keep rows with score <= threshold.")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=args.db_path)
    source = client.get_collection(args.source_collection)
    target = client.get_collection(args.target_collection)
    results = collect_matches(source, target, args.top_n, score_threshold=args.score_threshold)
    write_json(Path(args.output), results)


if __name__ == "__main__":
    main()
