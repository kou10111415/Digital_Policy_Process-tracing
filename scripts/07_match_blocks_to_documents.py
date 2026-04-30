from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import chromadb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json


def collect_matches(
    source_collection,
    target_collection,
    top_n: int,
    drop_self: bool = False,
    score_threshold: float | None = None,
) -> list[dict]:
    results = []
    source_rows = source_collection.get(include=["embeddings"])
    ids = source_rows.get("ids", [])
    embeddings = source_rows.get("embeddings", [])
    for source_id, embedding in zip(ids, embeddings):
        matches = target_collection.query(query_embeddings=[embedding], n_results=top_n + (1 if drop_self else 0), include=["distances", "documents"])
        for matched_id, score, doc_text in zip(matches["ids"][0], matches["distances"][0], matches.get("documents", [[]])[0]):
            if drop_self and matched_id == source_id:
                continue
            if score_threshold is not None and score is not None and score > score_threshold:
                continue
            results.append({
                "request_id": str(source_id),
                "matched_id": str(matched_id),
                "score": score,
                "text": doc_text,
            })
            if len([r for r in results if r["request_id"] == str(source_id)]) >= top_n:
                break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve the top candidate policy paragraphs for each extracted meeting block from a ChromaDB collection."
    )
    parser.add_argument("--db-path", required=True, help="Directory used by ChromaDB for persistent storage.")
    parser.add_argument("--source-collection", required=True, help="Collection containing embedded request or mention blocks.")
    parser.add_argument("--target-collection", required=True, help="Collection containing embedded document paragraphs.")
    parser.add_argument("--output", required=True, help="Output JSON path for candidate matches.")
    parser.add_argument("--top-n", type=int, default=20, help="Maximum number of candidates to keep per source block.")
    parser.add_argument("--score-threshold", type=float, default=None, help="Optional cosine-distance cutoff. Keep rows with score <= threshold.")
    parser.add_argument("--drop-self", action="store_true", help="Drop identical source and target IDs when matching within the same collection.")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=args.db_path)
    source = client.get_collection(args.source_collection)
    target = client.get_collection(args.target_collection)
    rows = collect_matches(
        source,
        target,
        args.top_n,
        drop_self=args.drop_self,
        score_threshold=args.score_threshold,
    )
    write_json(Path(args.output), rows)


if __name__ == "__main__":
    main()
