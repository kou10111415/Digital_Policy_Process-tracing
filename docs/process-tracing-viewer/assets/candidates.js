import {
  loadData,
  filterItems,
  getBlock,
  transitionLabel,
  relevantStageSections,
  bestPair,
  candidateArray,
  candidateCard,
  quotedPhrases,
  escapeHtml,
} from "./viewer-common.js";

function candidateSection(title, items, phrases) {
  if (!items.length) {
    return `
      <section class="candidate-section">
        <h3>${escapeHtml(title)}</h3>
        <p class="muted">候補なし</p>
      </section>
    `;
  }
  return `
    <section class="candidate-section">
      <h3>${escapeHtml(title)}</h3>
      <div class="candidate-grid">
        ${items.map((item) => candidateCard(item, phrases)).join("")}
      </div>
    </section>
  `;
}

function render(items, query = "") {
  const root = document.getElementById("results");
  const filtered = filterItems(items, query);
  root.innerHTML = filtered.map((item) => {
    const block = getBlock(item);
    const visible = new Set(relevantStageSections(item));
    const phrases = quotedPhrases(block);
    const bestPairLabel = bestPair(block);
    return `
      <article class="card">
        <div class="meta">
          <span class="pill">${escapeHtml(item.statement_id || "")}</span>
          <span>${escapeHtml(item.speaker || "")}</span>
          <span>${escapeHtml(transitionLabel(item))}</span>
          <span>${escapeHtml(block.reflected_stage || "")}</span>
          <span>confidence: ${escapeHtml(block.confidence ?? "")}</span>
        </div>
        <h2>${escapeHtml(block.request_summary || "要約なし")}</h2>
        <p class="statement-body">${escapeHtml(item.statement_text || "")}</p>
        <div class="best-pair-box">
          <span class="best-pair-label">採択候補</span>
          <span class="best-pair-value">${escapeHtml(bestPairLabel)}</span>
        </div>
        <p><strong>判定根拠:</strong> ${escapeHtml(block.reflection_basis?.change_description || "")}</p>
        ${visible.has("initial") ? candidateSection("議事録から見た素案候補", candidateArray(block, "initial_draft_candidates"), phrases) : ""}
        ${visible.has("draft") ? candidateSection("議事録から見た案候補", candidateArray(block, "draft_candidates"), phrases) : ""}
        ${visible.has("final") ? candidateSection("議事録から見た答申案候補", candidateArray(block, "final_draft_candidates"), phrases) : ""}
        ${visible.has("initial_to_draft") ? candidateSection("素案→案 候補", candidateArray(block, "initial_to_draft_candidates"), phrases) : ""}
        ${visible.has("draft_to_final") ? candidateSection("案→答申案 候補", candidateArray(block, "draft_to_final_candidates"), phrases) : ""}
      </article>
    `;
  }).join("");
}

async function boot() {
  try {
    const payload = await loadData();
    const items = payload.items || [];
    render(items);
    document.getElementById("query").addEventListener("input", (event) => {
      render(items, event.target.value);
    });
  } catch (error) {
    document.getElementById("results").innerHTML = `<article class="card"><p>${escapeHtml(error.message)}</p></article>`;
  }
}

boot();
