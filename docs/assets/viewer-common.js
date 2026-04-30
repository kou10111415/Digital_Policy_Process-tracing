export async function loadData() {
  if (window.__VIEWER_DATA__) {
    return window.__VIEWER_DATA__;
  }
  const response = await fetch("./data/viewer_data.json");
  if (!response.ok) {
    throw new Error("viewer_data.json could not be loaded");
  }
  return response.json();
}

export function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function highlightText(text = "", phrases = []) {
  let html = escapeHtml(text);
  const sorted = [...new Set((phrases || []).filter(Boolean))].sort((a, b) => b.length - a.length);
  for (const phrase of sorted) {
    const escaped = escapeHtml(phrase);
    if (!escaped || escaped.length < 2) {
      continue;
    }
    html = html.replaceAll(escaped, `<mark>${escaped}</mark>`);
  }
  return html;
}

export function getBlock(item) {
  return (item.blocks || [])[0] || {};
}

export function transitionLabel(item) {
  const transition = item.analysis_transition || {};
  const key = transition.transition || "";
  if (key === "initial_to_draft") {
    return "素案 -> 113回 -> 案";
  }
  if (key === "draft_to_final") {
    return "案 -> 115回 -> 答申案";
  }
  if (key === "final_review") {
    return "答申案 -> 116回";
  }
  return key;
}

export function transitionKey(item) {
  return item?.analysis_transition?.transition || "";
}

export function relevantStageSections(item) {
  const key = transitionKey(item);
  if (key === "initial_to_draft") {
    return ["initial", "draft", "initial_to_draft"];
  }
  if (key === "draft_to_final") {
    return ["draft", "final", "draft_to_final"];
  }
  if (key === "final_review") {
    return ["final"];
  }
  return ["initial", "draft", "final", "initial_to_draft", "draft_to_final"];
}

export function bestPair(block) {
  const pair = block.best_pair || {};
  const values = [pair.initial_draft_id, pair.draft_id, pair.final_draft_id].filter(Boolean);
  return values.length ? values.join(" -> ") : "未確定";
}

export function candidateArray(block, key) {
  return Array.isArray(block?.[key]) ? block[key] : [];
}

export function quotedPhrases(block) {
  const basis = block?.reflection_basis || {};
  return [basis.initial_quote, basis.draft_quote, basis.final_quote].filter(Boolean);
}

export function candidateCard(candidate, phrases = []) {
  const id = candidate?.matched_id || candidate?.id || "(no id)";
  const score = candidate?.score ?? "";
  const text = candidate?.text || "";
  return `
    <article class="candidate-card">
      <div class="candidate-meta">
        <span class="pill">${escapeHtml(id)}</span>
        <span>score: ${escapeHtml(score)}</span>
      </div>
      <div class="candidate-text">${highlightText(text, phrases)}</div>
    </article>
  `;
}

export function filterItems(items, query = "") {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return items;
  }
  return items.filter((item) => {
    const block = getBlock(item);
    const haystack = [
      item.statement_id,
      item.statement_text,
      item.speaker,
      block.request_summary,
      ...(candidateArray(block, "initial_draft_candidates").map((row) => row.text || "")),
      ...(candidateArray(block, "draft_candidates").map((row) => row.text || "")),
      ...(candidateArray(block, "final_draft_candidates").map((row) => row.text || "")),
    ].join(" ").toLowerCase();
    return haystack.includes(needle);
  });
}

export function blockLabel(item, index) {
  const block = getBlock(item);
  return `${index + 1}. ${block.request_summary || item.statement_id || "項目"}`;
}
