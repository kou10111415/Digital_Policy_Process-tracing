from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import write_json


def extract_paragraphs(html_path: Path) -> list[dict]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    rows = []
    for paragraph in soup.find_all("p"):
        pid = paragraph.get("id")
        if not pid:
            continue
        spans = paragraph.find_all(attrs={"data-pageno": True})
        anchors = []
        for span in spans:
            anchors.append({
                "page": span.get("data-pageno"),
                "line": span.get("data-lineno"),
                "text": span.get_text(strip=True),
            })
        rows.append({
            "id": pid,
            "text": paragraph.get_text(strip=True),
            "anchors": anchors,
            "source_html": html_path.name,
            "source_stage": "initial_draft",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the initial draft HTML into paragraph-level JSON with stable paragraph IDs and page/line anchors."
    )
    parser.add_argument("--input", required=True, help="Path to the initial-draft HTML file.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    args = parser.parse_args()

    paragraphs = extract_paragraphs(Path(args.input))
    payload = {
        "document_type": "initial_draft",
        "paragraphs": paragraphs,
    }
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
