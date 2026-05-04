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

function column(title, candidate, phrases) {
  return `
    <section class="compare-column">
      <h3>${escapeHtml(title)}</h3>
      ${candidate ? candidateCard(candidate, phrases) : '<p class="muted">候補なし</p>'}
    </section>
  `;
}

function render(items, query = "") {
  const filtered = filterItems(items, query).filter((item) => getBlock(item).reflected === true);
  const sidebar = document.getElementById("sidebar");
  const detail = document.getElementById("detail");
  if (!filtered.length) {
    sidebar.innerHTML = "";
    detail.innerHTML = '<article class="card"><p>変更が加えられたと確定した項目がありません。</p></article>';
    return;
  }
  if (currentIndex >= filtered.length) {
    currentIndex = 0;
  }
  sidebar.innerHTML = filtered.map((item, index) => `
    <button class="sidebar-item ${index === currentIndex ? "active" : ""}" data-index="${index}">
      ${escapeHtml(blockLabel(item, index))}
    </button>
  `).join("");

  const item = filtered[currentIndex];
  const block = getBlock(item);
  const phrases = quotedPhrases(block);
  const transition = transitionKey(item);
  const initial = candidateArray(block, "initial_draft_candidates")[0];
  const draft = candidateArray(block, "draft_candidates")[0];
  const finalDraft = candidateArray(block, "final_draft_candidates")[0];
  const stageColumns = [];
  if (transition === "initial_to_draft" || !transition) {
    stageColumns.push(column("素案", initial, phrases));
    stageColumns.push(column("案", draft, phrases));
  } else if (transition === "draft_to_final") {
    stageColumns.push(column("案", draft, phrases));
    stageColumns.push(column("答申案", finalDraft, phrases));
  } else if (transition === "final_review") {
    stageColumns.push(column("答申案", finalDraft, phrases));
  } else {
    stageColumns.push(column("素案", initial, phrases));
    stageColumns.push(column("案", draft, phrases));
    stageColumns.push(column("答申案", finalDraft, phrases));
  }

  detail.innerHTML = `
    <article class="card">
      <div class="meta">
        <span class="pill">${escapeHtml(item.statement_id || "")}</span>
        <span>${escapeHtml(item.speaker || "")}</span>
        <span>${escapeHtml(transitionLabel(item))}</span>
      </div>
      <h2>${escapeHtml(block.request_summary || "")}</h2>
      <p class="statement-body">${escapeHtml(item.statement_text || "")}</p>
      <section class="compare-grid">
        <section class="compare-column">
          <h3>議事録</h3>
          <div class="candidate-text">${escapeHtml(item.statement_text || "")}</div>
        </section>
        ${stageColumns.join("")}
      </section>
    </article>
  `;

  document.querySelectorAll(".sidebar-item").forEach((button) => {
    button.addEventListener("click", () => {
      currentIndex = Number(button.dataset.index || 0);
      render(items, document.getElementById("query").value);
    });
  });
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
