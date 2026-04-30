from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import load_openai_api_key, read_json, write_jsonl


SYSTEM = """You are an expert analyst of Japanese administrative policy documents.
Your task is ONLY to judge whether each requested change was reflected
across the policy drafting stages.

Rules:
- Be conservative: reflected=true ONLY when there is clear evidence in the provided candidate texts.
- Do NOT guess content that is not present.
- Related minutes are context only; they cannot prove reflection by themselves.
- Treat EACH block independently; do NOT use candidates from other blocks.
- Respect the meeting sequence:
  - meeting 113 contributes to initial draft -> draft
  - meeting 115 contributes to draft -> final draft
  - meeting 116 is a final-draft review/mention stage
- Do not infer a direct initial draft -> final draft reflection unless the task explicitly says so.
"""


def choose_best(rows: list[dict], *, key: str = "score") -> dict | None:
    candidates = [row for row in rows if row.get(key) is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda row: row[key])


def infer_missing_best_pair(block: dict, link_threshold: float | None) -> dict:
    best_pair = dict(block.get("best_pair", {}))
    inference = {
        "used": False,
        "filled_fields": [],
    }

    def within_threshold(row: dict | None) -> bool:
        if row is None:
            return False
        score = row.get("score")
        return score is not None and (link_threshold is None or score <= link_threshold)

    initial_id = best_pair.get("initial_draft_id")
    draft_id = best_pair.get("draft_id")
    final_id = best_pair.get("final_draft_id")

    if initial_id and not draft_id:
        row = choose_best([candidate for candidate in block.get("initial_to_draft_candidates", []) if candidate.get("request_id") == initial_id])
        if within_threshold(row):
            best_pair["draft_id"] = row["matched_id"]
            draft_id = row["matched_id"]
            inference["used"] = True
            inference["filled_fields"].append({
                "field": "draft_id",
                "source": "initial_to_draft_candidates",
                "score": row.get("score"),
                "from_id": initial_id,
                "to_id": draft_id,
            })

    if draft_id and not initial_id:
        row = choose_best([candidate for candidate in block.get("initial_to_draft_candidates", []) if candidate.get("matched_id") == draft_id])
        if within_threshold(row):
            best_pair["initial_draft_id"] = row["request_id"]
            initial_id = row["request_id"]
            inference["used"] = True
            inference["filled_fields"].append({
                "field": "initial_draft_id",
                "source": "initial_to_draft_candidates",
                "score": row.get("score"),
                "from_id": draft_id,
                "to_id": initial_id,
            })

    if draft_id and not final_id:
        row = choose_best([candidate for candidate in block.get("draft_to_final_candidates", []) if candidate.get("request_id") == draft_id])
        if within_threshold(row):
            best_pair["final_draft_id"] = row["matched_id"]
            final_id = row["matched_id"]
            inference["used"] = True
            inference["filled_fields"].append({
                "field": "final_draft_id",
                "source": "draft_to_final_candidates",
                "score": row.get("score"),
                "from_id": draft_id,
                "to_id": final_id,
            })

    if final_id and not draft_id:
        row = choose_best([candidate for candidate in block.get("draft_to_final_candidates", []) if candidate.get("matched_id") == final_id])
        if within_threshold(row):
            best_pair["draft_id"] = row["request_id"]
            draft_id = row["request_id"]
            inference["used"] = True
            inference["filled_fields"].append({
                "field": "draft_id",
                "source": "draft_to_final_candidates",
                "score": row.get("score"),
                "from_id": final_id,
                "to_id": draft_id,
            })

    return {
        "best_pair": best_pair,
        "best_pair_inference": inference,
    }


def fmt_candidates(title: str, candidates: list[dict]) -> str:
    lines = [f"### {title}"]
    if not candidates:
        return "\n".join(lines + ["(none)"])
    for candidate in candidates:
        lines.append(
            f"[ID: {candidate.get('matched_id', candidate.get('id'))}] "
            f"(score: {candidate.get('score')})\n"
            f"{candidate.get('text', '')}"
        )
    return "\n\n".join(lines)


def build_user_prompt(payload: dict) -> str:
    blocks_txt = []
    for block in payload.get("blocks", []):
        blocks_txt.append(
            f"""
## Block {block.get('block_index', 0)}
request_summary: {block.get('request_summary', '')}

{fmt_candidates("Initial draft candidates (素案)", block.get("initial_draft_candidates", []))}

{fmt_candidates("Draft candidates (案)", block.get("draft_candidates", []))}

{fmt_candidates("Final draft candidates (答申案)", block.get("final_draft_candidates", []))}

{fmt_candidates("Initial -> Draft document candidates", block.get("initial_to_draft_candidates", []))}

{fmt_candidates("Draft -> Final document candidates", block.get("draft_to_final_candidates", []))}

{fmt_candidates("Related minutes (context only)", block.get("minutes_candidates", []))}
""".strip()
        )

    return f"""
You are given one statement with one or more request blocks.
Judge each block independently.

statement_id: {payload.get('statement_id')}
meeting_id: {payload.get('meeting_id')}
speaker: {payload.get('speaker')}
statement_text: {payload.get('statement_text')}
analysis_transition: {payload.get('analysis_transition')}

{chr(10).join(blocks_txt)}

Return ONLY JSON in this schema:
{{
  "statement_id": "{payload.get('statement_id')}",
  "statement_text": "...",
  "blocks": [
    {{
      "block_index": 0,
      "request_summary": "...",
      "reflected": true,
      "reflected_stage": "initial_to_draft|draft_to_final|final_review|no_evidence",
      "best_pair": {{
        "initial_draft_id": "... or null",
        "draft_id": "... or null",
        "final_draft_id": "... or null"
      }},
      "reflection_basis": {{
        "change_type": "text_added|text_modified|text_removed|footnote_added|reference_only|no_evidence",
        "change_description": "...",
        "initial_quote": "...",
        "draft_quote": "...",
        "final_quote": "..."
      }},
      "confidence": 0.0
    }}
  ]
}}
""".strip()


def call_llm(client: OpenAI, model: str, payload: dict) -> dict:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_user_prompt(payload)},
        ],
        reasoning={"effort": "none"},
        text={"verbosity": "medium"},
    )
    return json.loads(getattr(response, "output_text", ""))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask the LLM to judge whether each extracted request was reflected in the document revision candidates."
    )
    parser.add_argument("--input", required=True, help="Input JSON produced by 09_build_pipeline_json.py")
    parser.add_argument("--output-jsonl", required=True, help="Output JSONL path for reflection judgements.")
    parser.add_argument("--model", default="gpt-5.5", help="OpenAI model used for the judgement step.")
    parser.add_argument("--api-key-file", default=None, help="Optional text file containing an OpenAI API key.")
    parser.add_argument("--infer-missing-pairs", action="store_true", help="Optionally backfill missing best_pair IDs from document-stage link candidates.")
    parser.add_argument("--pair-link-threshold", type=float, default=0.55, help="Maximum cosine distance allowed when inferring missing best_pair IDs.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_json(Path(args.input))
    if args.dry_run:
        results = [{
            "statement_id": row["statement_id"],
            "meeting_id": row.get("meeting_id", ""),
            "speaker": row.get("speaker", ""),
            "statement_text": row.get("statement_text", ""),
            "analysis_transition": row.get("analysis_transition", {}),
            "blocks": [{
                "block_index": block.get("block_index", 0),
                "request_summary": block.get("request_summary", ""),
                "initial_draft_candidates": block.get("initial_draft_candidates", []),
                "draft_candidates": block.get("draft_candidates", []),
                "final_draft_candidates": block.get("final_draft_candidates", []),
                "initial_to_draft_candidates": block.get("initial_to_draft_candidates", []),
                "draft_to_final_candidates": block.get("draft_to_final_candidates", []),
                "minutes_candidates": block.get("minutes_candidates", []),
                "reflected": False,
                "reflected_stage": "no_evidence",
                "best_pair": {
                    "initial_draft_id": None,
                    "draft_id": None,
                    "final_draft_id": None,
                },
                "reflection_basis": {
                    "change_type": "no_evidence",
                    "change_description": "dry-run",
                    "initial_quote": "",
                    "draft_quote": "",
                    "final_quote": "",
                },
                "confidence": 0.0,
            } for block in row.get("blocks", [])],
            "model": args.model,
        } for row in rows]
    else:
        client = OpenAI(api_key=load_openai_api_key(args.api_key_file))
        results = []
        for row in rows:
            result = call_llm(client, args.model, row)
            result["meeting_id"] = row.get("meeting_id", "")
            result["analysis_transition"] = row.get("analysis_transition", {})
            for block, original in zip(result.get("blocks", []), row.get("blocks", [])):
                block["initial_draft_candidates"] = original.get("initial_draft_candidates", [])
                block["draft_candidates"] = original.get("draft_candidates", [])
                block["final_draft_candidates"] = original.get("final_draft_candidates", [])
                block["initial_to_draft_candidates"] = original.get("initial_to_draft_candidates", [])
                block["draft_to_final_candidates"] = original.get("draft_to_final_candidates", [])
                block["minutes_candidates"] = original.get("minutes_candidates", [])
                if args.infer_missing_pairs:
                    inferred = infer_missing_best_pair(block, args.pair_link_threshold)
                    block["best_pair"] = inferred["best_pair"]
                    block["best_pair_inference"] = inferred["best_pair_inference"]
            result["speaker"] = row.get("speaker", "")
            result["model"] = args.model
            results.append(result)
            time.sleep(0.5)

    write_jsonl(Path(args.output_jsonl), results)


if __name__ == "__main__":
    main()
