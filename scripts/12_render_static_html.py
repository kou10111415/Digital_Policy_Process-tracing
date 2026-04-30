from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCRIPT_TAG = '<script>window.__VIEWER_DATA__ = __DATA__;</script>'


def inject_data(html: str, payload: dict) -> str:
    data_script = SCRIPT_TAG.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    if "window.__VIEWER_DATA__" in html:
        return html
    return re.sub(r"</body>", data_script + "\n</body>", html, count=1, flags=re.IGNORECASE)


def render_one(input_html: Path, output_html: Path, payload: dict) -> None:
    html = input_html.read_text(encoding="utf-8")
    output_html.write_text(inject_data(html, payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed viewer data JSON into the HTML viewers and write standalone HTML files."
    )
    parser.add_argument("--data", required=True, help="Input viewer data JSON.")
    parser.add_argument("--docs-dir", required=True, help="Directory containing the base HTML viewer files.")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    payload = json.loads(Path(args.data).read_text(encoding="utf-8"))

    targets = [
        ("candidates.html", "candidates_standalone.html"),
        ("meeting_viewer.html", "meeting_viewer_standalone.html"),
        ("comparison_viewer.html", "comparison_viewer_standalone.html"),
    ]
    for src, dst in targets:
        render_one(docs_dir / src, docs_dir / dst, payload)


if __name__ == "__main__":
    main()
