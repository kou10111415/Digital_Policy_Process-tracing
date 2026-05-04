# Digital Policy Process-tracing

審議会議事録の発言から政策文書改訂への反映候補を抽出し、判定結果を静的 HTML ビューアで確認できるようにするためのリポジトリです。対象データは TEI/XML 議事録と、複数版の政策文書 HTML です。

このリポジトリでは、発言の中から政策文書の変更要求や変更言及を LLM で抽出し、段落埋め込みによる候補探索と LLM による反映判定を組み合わせて、検証可能な JSON / JSONL / HTML を生成します。

関連プロジェクト:

- https://github.com/cm3/v2p-tracker
- https://github.com/kou10111415/env_meeting_annotated

## What This Repository Does

- TEI/XML 議事録から会議単位の発言を抽出する
- 発言をチャンク化し、LLM で要求ブロックまたは変更言及ブロックを抽出する
- 抽出結果を主表 JSON に整理する
- 政策文書の各段落と要求ブロックを埋め込みベクトル化する
- ベクトル検索で、発言から関連しそうな段落候補を複数版にまたがって収集する
- 文書版どうしの対応候補も別途生成する
- LLM に候補群を比較させ、実際に反映があったかを判定する
- 判定結果を JSON と静的 HTML ビューアにまとめる

## Repository Layout

```text
Digital_Policy_Process-tracing/
├── ENV_113-116.xml
├── sources/
│   ├── tei/
│   │   └── ENV_113-116.xml
│   ├── html/
│   │   ├── initial_draft/
│   │   │   └── env6plan_initial_draft.html
│   │   ├── draft/
│   │   │   └── env6plan_draft.html
│   │   └── final_draft/
│   │       └── env6plan_final_draft.html
│   └── viewer_assets/
│       ├── env_reference/
│       └── v2p_reference/
├── scripts/
│   ├── 01_extract_meeting_blocks.py
│   ├── 02_normalize_initial_draft.py
│   ├── 03_parse_llm_blocks.py
│   ├── 04_embed_documents.py
│   ├── 05_embed_master_blocks.py
│   ├── 06_import_embeddings_to_chromadb.py
│   ├── 07_match_blocks_to_documents.py
│   ├── 08_match_documents.py
│   ├── 09_build_pipeline_json.py
│   ├── 10_judge_reflection.py
│   ├── 11_build_viewer_data.py
│   ├── 12_render_static_html.py
│   └── common.py
├── data/
│   ├── raw/
│   ├── intermediate/
│   └── results/
├── docs/
│   ├── index.html
│   ├── candidates.html
│   ├── meeting_viewer.html
│   ├── comparison_viewer.html
│   ├── data/
│   └── assets/
├── requirements.txt
├── v2p_getinfo.py
└── v2p_getinfo.ipynb
```

## Data Model

主な中間データは次の 3 系統です。

`master JSON`

- `content_id`
- `content_key`
- `meeting_id`
- `statement_id`
- `speaker`
- `statement_text`
- `content`
- `label`
- `other_reference`
- `page_line`
- `reason`
- `label_type`

`candidate JSON`

- `request_id`
- `matched_id`
- `score`
- `text`

`judgement JSON / JSONL`

- `statement_id`
- `meeting_id`
- `analysis_transition`
- `blocks[]`
- `best_pair.initial_draft_id`
- `best_pair.draft_id`
- `best_pair.final_draft_id`
- `reflected_stage`
- `reflection_basis`
- `confidence`

## Pipeline Overview

1. `01_extract_meeting_blocks.py`
   - TEI/XML から会議ごとの発言を読み取り、LLM で要求または言及を抽出して JSONL に保存します。
2. `03_parse_llm_blocks.py`
   - LLM 抽出ログを、後続処理で使いやすい主表 JSON に整形します。
3. `02_normalize_initial_draft.py`
   - 素案 HTML を段落単位の JSON に変換します。
4. `04_embed_documents.py`
   - 素案・案・答申案の段落埋め込みを生成します。
5. `05_embed_master_blocks.py`
   - 主表 JSON のうち、対象ラベルの要求ブロックを埋め込みます。
6. `06_import_embeddings_to_chromadb.py`
   - 段落と要求ブロックの埋め込みを ChromaDB コレクションに登録します。
7. `07_match_blocks_to_documents.py`
   - 要求ブロックから、各文書版の関連段落候補を取得します。
8. `08_match_documents.py`
   - 文書版どうしの段落対応候補を取得します。
9. `09_build_pipeline_json.py`
   - 主表と候補群をまとめて、反映判定用 JSON を組み立てます。
10. `10_judge_reflection.py`
   - LLM が候補群を比較し、反映の有無と根拠を JSONL として出力します。
11. `11_build_viewer_data.py`
   - 判定結果をビューア用 JSON にまとめます。
12. `12_render_static_html.py`
   - ビューア用 JSON とアセットから静的 HTML ビューアを生成します。

## Typical Outputs

主に次の成果物が生成されます。

- `data/intermediate/*.jsonl`
  - 発言抽出ログ、埋め込み、判定結果など
- `data/intermediate/*.json`
  - 主表 JSON、候補 JSON、判定入力 JSON
- `docs/data/*.json`
  - ビューアが読む集約済み JSON
- `docs/*.html`
  - 静的 HTML ビューア本体

CSV は任意の補助出力として利用できますが、このリポジトリの本流は JSON / JSONL / HTML ベースです。

## Retrieval and Judgement Defaults

候補探索は、取りこぼしを減らすために広めに集める前提です。

- `07_match_blocks_to_documents.py`
  - `--top-n 30` を推奨
- `08_match_documents.py`
  - `--top-n 30` を推奨
- `07` と `08` の `--score-threshold`
  - 原則として未指定
- `10_judge_reflection.py`
  - `--infer-missing-pairs --pair-link-threshold 0.55` を推奨

`--infer-missing-pairs` を指定すると、版間リンク候補を使って `best_pair` の欠損 ID を補完できます。これは保守的な補完用オプションであり、常時必須ではありません。

## Meeting Sequence Assumption

既定の分析前提は次の通りです。

- `素案 -> 113回 -> 案`
- `案 -> 115回 -> 答申案`
- `答申案 -> 116回`

この前提に基づき、判定時には会議ごとに比較対象の文書段階を切り替えます。

## Viewer Files

`docs/` には 3 種類のビューアがあります。

- `candidates.html`
  - 候補一覧を確認するビューア
- `meeting_viewer.html`
  - 議事録起点で確認するビューア
- `comparison_viewer.html`
  - 発言と複数版段落を並べて比較するビューア

## Notes

- `v2p_getinfo.py` は `10_judge_reflection.py` の実行入口として使えます。
- 素案以外の文書は HTML をそのまま段落走査し、素案は `02_normalize_initial_draft.py` の JSON を介して扱う想定です。
- 議事録関連候補は文脈参照用であり、単独では反映の証拠として扱わない設計です。

## License and Reuse

再配布や公開時には、入力元データの利用条件と、API 利用先の規約を別途確認してください。
