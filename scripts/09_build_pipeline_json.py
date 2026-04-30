from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import read_json, write_json


def group_matches(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["request_id"])].append(row)
    return grouped


def collect_linked_candidates(seed_candidates: list[dict], pair_map: dict[str, list[dict]], max_candidates: int, score_threshold: float | None) -> list[dict]:
    collected = []
    seen = set()
    for candidate in seed_candidates:
        source_id = str(candidate.get("matched_id", candidate.get("id", "")))
        for linked in pair_map.get(source_id, []):
            key = (linked.get("request_id"), linked.get("matched_id"))
            if key in seen:
                continue
            if score_threshold is not None and linked.get("score") is not None and linked["score"] > score_threshold:
                continue
            seen.add(key)
            collected.append(linked)
            if len(collected) >= max_candidates:
                return collected
    return collected


def infer_transition(meeting_id: str, statement_id: str) -> dict[str, str]:
    key = f"{meeting_id} {statement_id}"
    if "113" in key:
        return {
            "source_stage": "initial_draft",
            "target_stage": "draft",
            "transition": "initial_to_draft",
            "description": "第113回は素案から案への改訂に寄与する会議として扱う。",
        }
    if "115" in key:
        return {
            "source_stage": "draft",
            "target_stage": "final_draft",
            "transition": "draft_to_final",
            "description": "第115回は案から答申案への改訂に寄与する会議として扱う。",
        }
    if "116" in key:
        return {
            "source_stage": "final_draft",
            "target_stage": "final_draft",
            "transition": "final_review",
            "description": "第116回は答申案に対する確認・言及の会議として扱う。",
        }
    return {
        "source_stage": "unknown",
        "target_stage": "unknown",
        "transition": "unknown",
        "description": "会議段階を自動判定できなかった。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble the normalized master table and all candidate lists into a single JSON payload for reflection judgement."
    )
    parser.add_argument("--master", required=True, help="Master JSON produced by 03_parse_llm_blocks.py")
    parser.add_argument("--initial-candidates", required=True, help="Request-to-initial-draft candidate JSON.")
    parser.add_argument("--draft-candidates", required=True, help="Request-to-draft candidate JSON.")
    parser.add_argument("--final-candidates", required=True, help="Request-to-final-draft candidate JSON.")
    parser.add_argument("--minutes-candidates", required=True, help="Request-to-related-minutes candidate JSON.")
    parser.add_argument("--initial-to-draft-candidates", default=None, help="Optional paragraph-link candidates from initial draft to draft.")
    parser.add_argument("--draft-to-final-candidates", default=None, help="Optional paragraph-link candidates from draft to final draft.")
    parser.add_argument("--output", required=True, help="Output JSON path for reflection-judgement input.")
    parser.add_argument("--score-threshold", type=float, default=None, help="Optional cosine-distance cutoff applied before payload assembly.")
    parser.add_argument("--max-candidates", type=int, default=20, help="Maximum number of candidates retained per block and candidate type.")
    args = parser.parse_args()

    master_rows = read_json(Path(args.master))
    initial_rows = group_matches(read_json(Path(args.initial_candidates)))
    draft_rows = group_matches(read_json(Path(args.draft_candidates)))
    final_rows = group_matches(read_json(Path(args.final_candidates)))
    minute_rows = group_matches(read_json(Path(args.minutes_candidates)))
    initial_to_draft_rows = group_matches(read_json(Path(args.initial_to_draft_candidates))) if args.initial_to_draft_candidates else {}
    draft_to_final_rows = group_matches(read_json(Path(args.draft_to_final_candidates))) if args.draft_to_final_candidates else {}

    payload = []
    for row in master_rows:
        content_id = str(row["content_id"])

        def filter_rows(rows: list[dict]) -> list[dict]:
            kept = rows
            if args.score_threshold is not None:
                kept = [item for item in kept if item.get("score") is not None and item["score"] <= args.score_threshold]
            return kept[: args.max_candidates]

        initial_candidates = filter_rows(initial_rows.get(content_id, []))
        draft_candidates = filter_rows(draft_rows.get(content_id, []))
        final_candidates = filter_rows(final_rows.get(content_id, []))
        transition = infer_transition(row.get("meeting_id", ""), row["statement_id"])

        if transition["transition"] == "initial_to_draft":
            final_candidates = []
        elif transition["transition"] == "draft_to_final":
            initial_candidates = []
        elif transition["transition"] == "final_review":
            initial_candidates = []
            draft_candidates = []

        payload.append({
            "statement_id": row["statement_id"],
            "content_id": content_id,
            "meeting_id": row.get("meeting_id", ""),
            "speaker": row.get("speaker", ""),
            "statement_text": row.get("statement_text", ""),
            "label": row.get("label", ""),
            "reason": row.get("reason", ""),
            "analysis_transition": transition,
            "blocks": [{
                "block_index": 0,
                "request_summary": row.get("content", ""),
                "initial_draft_candidates": initial_candidates,
                "draft_candidates": draft_candidates,
                "final_draft_candidates": final_candidates,
                "minutes_candidates": filter_rows(minute_rows.get(content_id, [])),
                "initial_to_draft_candidates": collect_linked_candidates(
                    initial_candidates,
                    initial_to_draft_rows,
                    args.max_candidates,
                    args.score_threshold,
                ) if transition["transition"] == "initial_to_draft" else [],
                "draft_to_final_candidates": collect_linked_candidates(
                    draft_candidates,
                    draft_to_final_rows,
                    args.max_candidates,
                    args.score_threshold,
                ) if transition["transition"] == "draft_to_final" else [],
            }],
        })

    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
