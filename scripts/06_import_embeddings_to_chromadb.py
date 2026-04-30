from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import paragraph or block embeddings from JSONL into a ChromaDB collection."
    )
    parser.add_argument("--db-path", required=True, help="Directory used by ChromaDB for persistent storage.")
    parser.add_argument("--collection", required=True, help="Collection name to create or update.")
    parser.add_argument("--input", required=True, help="Input JSONL containing embeddings.")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=args.db_path)
    collection = client.get_or_create_collection(args.collection, metadata={"hnsw:space": "cosine"})

    for row in read_jsonl(Path(args.input)):
        collection.add(
            ids=[str(row["id"])],
            embeddings=[row["embedding"]],
            documents=[row.get("text", "")],
            metadatas=[{
                "stage": row.get("stage", ""),
                "statement_id": row.get("statement_id", ""),
                "meeting_id": row.get("meeting_id", ""),
                "source_html": row.get("source_html", ""),
            }],
        )


if __name__ == "__main__":
    main()
