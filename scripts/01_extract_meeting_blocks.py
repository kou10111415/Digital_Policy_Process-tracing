from __future__ import annotations

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import ROOT, load_openai_api_key


NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

PROMPTS = {
    "request": """以下の発言は、行政計画の文書に関する議論中の1人の委員の発言です。

ここでの「要求」とは、行政計画文書の明確な変更を迫る要求のことを指します。議事進行など、行政計画文書の変更に関わらない要求については無視してください。

参照されたページや行があれば、その情報に加えて「見え消し版」「溶け込み版」などの版の種類も取得してください。

この発言に含まれる要求を、まとまりごとに分けて抽出してください。

JSON 配列のみを返してください。各要素は以下のキーを持ちます:
- 内容
- 要求あり
- 他の委員の発言参照
- 参照されたページ・行
- 理由

発言: 「{chunk}」""",
    "mention": """以下の発言は、行政計画の文書に関する議論中の1人の委員の発言です。

ここでの「変更の言及」とは、環境基本計画の案が変更された箇所や内容についての言及のことを指します。

参照されたページや行があれば、その情報に加えて版の種類も取得してください。

この発言に含まれる変更言及を、まとまりごとに分けて抽出してください。

JSON 配列のみを返してください。各要素は以下のキーを持ちます:
- 内容
- 言及あり
- 他の委員の発言参照
- 参照されたページ・行
- 理由

発言: 「{chunk}」""",
}


def split_segments(segments, max_chars: int = 800) -> list[str]:
    chunks = []
    current = []
    total = 0
    for seg in segments:
        text = "".join(seg.itertext()).strip()
        if not text:
            continue
        if total + len(text) > max_chars and current:
            chunks.append(" ".join(current))
            current = [text]
            total = len(text)
        else:
            current.append(text)
            total += len(text)
    if current:
        chunks.append(" ".join(current))
    return chunks


def load_persons(root) -> dict[str, str]:
    persons = {}
    for person in root.findall(".//tei:person", NS):
        pid = person.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        pers_name = person.find(".//tei:persName", NS)
        if pers_name is None:
            persons[f"#{pid}"] = "(不明)"
            continue
        surname = pers_name.find("tei:surname", NS)
        forename = pers_name.find("tei:forename", NS)
        if surname is not None and forename is not None:
            persons[f"#{pid}"] = (surname.text or "").strip() + (forename.text or "").strip()
        else:
            persons[f"#{pid}"] = "".join(pers_name.itertext()).strip()
    return persons


def call_llm(client: OpenAI, mode: str, chunk: str, model: str) -> str:
    prompt = PROMPTS[mode].format(chunk=chunk)
    response = client.responses.create(
        model=model,
        input=prompt,
        reasoning={"effort": "none"},
        text={"verbosity": "medium"},
    )
    content = getattr(response, "output_text", "")
    if not content or not content.strip():
        raise ValueError("Empty response from API")
    return content.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read one meeting from TEI/XML, split each utterance into chunks, and ask the LLM to extract request or mention blocks."
    )
    parser.add_argument("--xml", default=str(ROOT / "sources/tei/ENV_113-116.xml"), help="Path to the source TEI/XML file.")
    parser.add_argument("--meeting-id", required=True, help="Meeting identifier in the TEI file, for example: meeting-113")
    parser.add_argument("--mode", choices=("request", "mention"), default="request", help="Extraction mode: 'request' finds requested document changes, 'mention' finds mentions of changes.")
    parser.add_argument("--model", default="gpt-5.5", help="OpenAI model used for extraction.")
    parser.add_argument("--output", required=True, help="Output JSONL path for raw extraction logs.")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on the number of utterances to process. Use 0 for all utterances.")
    parser.add_argument("--api-key-file", default=None, help="Optional text file containing an OpenAI API key.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tree = ET.parse(args.xml)
    root = tree.getroot()
    persons = load_persons(root)
    meeting = root.find(f".//tei:*[@xml:id='{args.meeting_id}']", NS)
    if meeting is None:
        raise SystemExit(f"meeting not found: {args.meeting_id}")

    utterances = meeting.findall(".//tei:u", NS)
    client = None if args.dry_run else OpenAI(api_key=load_openai_api_key(args.api_key_file))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for index, utterance in enumerate(utterances):
            if args.limit and index >= args.limit:
                break

            uid = utterance.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")
            who = utterance.attrib.get("who", "")
            speaker = persons.get(who, who)
            segments = utterance.findall(".//tei:seg", NS)
            chunk_texts = split_segments(segments)

            for chunk in chunk_texts:
                if len(chunk.strip()) <= 15:
                    payload = [{
                        "内容": chunk,
                        "要求あり" if args.mode == "request" else "言及あり": "No",
                        "他の委員の発言参照": "No",
                        "参照されたページ・行": "",
                        "理由": "15文字以下なのでスキップされた",
                    }]
                    raw_response = json.dumps(payload, ensure_ascii=False)
                elif args.dry_run:
                    raw_response = json.dumps([{
                        "内容": chunk,
                        "要求あり" if args.mode == "request" else "言及あり": "DryRun",
                        "他の委員の発言参照": "No",
                        "参照されたページ・行": "",
                        "理由": "dry-run",
                    }], ensure_ascii=False)
                else:
                    raw_response = call_llm(client, args.mode, chunk, args.model)

                record = {
                    "発言ID": uid,
                    "発言者": speaker,
                    "発言原文": chunk,
                    "mode": args.mode,
                    "meeting_id": args.meeting_id,
                    "raw_response": raw_response,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                time.sleep(0.5)


if __name__ == "__main__":
    main()
