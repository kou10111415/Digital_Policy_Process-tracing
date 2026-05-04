import {
  loadData,
  filterItems,
  getBlock,
  blockLabel,
  transitionLabel,
  transitionKey,
  candidateArray,
  candidateCard,
  quotedPhrases,
  escapeHtml,
} from "./viewer-common.js";

let cache = [];
let currentIndex = 0;

function listMarkup(items) {
  return items.map((item, index) => `
    <button class="sidebar-item ${index === currentIndex ? "active" : ""}" data-index="${index}">
      ${escapeHtml(blockLabel(item, index))}
    </button>
  `).join("");
}

function detailMarkup(item) {
  const block = getBlock(item);
  const phrases = quotedPhrases(block);
  const transition = transitionKey(item);
  const initial = candidateArray(block, "initial_draft_candidates")[0];
  const draft = candidateArray(block, "draft_candidates")[0];
  const finalDraft = candidateArray(block, "final_draft_candidates")[0];
  const stagePanels = [];
  if (transition === "initial_to_draft" || !transition) {
    stagePanels.push(`
      <h2>素案</h2>
      ${initial ? candidateCard(initial, phrases) : '<p class="muted">候補なし</p>'}
      <h2>案</h2>
      ${draft ? candidateCard(draft, phrases) : '<p class="muted">候補なし</p>'}
    `);
  }
  if (transition === "draft_to_final") {
    stagePanels.push(`
      <h2>案</h2>
      ${draft ? candidateCard(draft, phrases) : '<p class="muted">候補なし</p>'}
      <h2>答申案</h2>
      ${finalDraft ? candidateCard(finalDraft, phrases) : '<p class="muted">候補なし</p>'}
    `);
  }
  if (transition === "final_review") {
    stagePanels.push(`
      <h2>答申案</h2>
      ${finalDraft ? candidateCard(finalDraft, phrases) : '<p class="muted">候補なし</p>'}
    `);
  }
  return `
    <section class="meeting-shell">
      <div class="meeting-panel">
        <h2>議事録</h2>
        <div class="meta">
          <span class="pill">${escapeHtml(item.statement_id || "")}</span>
          <span>${escapeHtml(item.speaker || "")}</span>
          <span>${escapeHtml(transitionLabel(item))}</span>
        </div>
        <h3>要求要約</h3>
        <p class="request-summary">${escapeHtml(block.request_summary || "")}</p>
        <h3>発言本文</h3>
        <div class="statement-body">${escapeHtml(item.statement_text || "")}</div>
        <h3>判定</h3>
        <p>${escapeHtml(block.reflected_stage || "")} / confidence ${escapeHtml(block.confidence ?? "")}</p>
      </div>
      <div class="meeting-panel">
        ${stagePanels.join("")}
      </div>
    </section>
  `;
}

function attachHandlers(items) {
  document.querySelectorAll(".sidebar-item").forEach((button) => {
    button.addEventListener("click", () => {
      currentIndex = Number(button.dataset.index || 0);
      render(items, document.getElementById("query").value);
    });
  });
}

function render(items, query = "") {
  const filtered = filterItems(items, query).filter((item) => getBlock(item).reflected === true);
  if (!filtered.length) {
    document.getElementById("sidebar").innerHTML = "";
    document.getElementById("detail").innerHTML = '<article class="card"><p>変更が加えられたと確定した項目がありません。</p></article>';
    return;
  }
  if (currentIndex >= filtered.length) {
    currentIndex = 0;
  }
  document.getElementById("sidebar").innerHTML = listMarkup(filtered);
  document.getElementById("detail").innerHTML = detailMarkup(filtered[currentIndex]);
  attachHandlers(filtered);
}

async function boot() {
  try {
    const payload = await loadData();
    cache = payload.items || [];
    render(cache);
    document.getElementById("query").addEventListener("input", (event) => {
      currentIndex = 0;
      render(cache, event.target.value);
    });
  } catch (error) {
    document.getElementById("detail").innerHTML = `<article class="card"><p>${escapeHtml(error.message)}</p></article>`;
  }
}

boot();
