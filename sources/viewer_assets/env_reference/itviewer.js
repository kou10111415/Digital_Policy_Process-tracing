import { addAnnotationMarkers } from './annotation.js';

const docInfo = {
  x: { title: "議事録", src: "./minutes113.html" },
  y: { title: "計画案", src: "./env6plan_draft.html" },
  z: { title: "計画素案", src: "./env6plan_initial_draft.html" },
  info: { title: "関連情報", src: "" }
};

const layoutOptions = {
  "solo": ["x"],
  "x-left-y-right": ["x", "y"],
  "x-left-z-right": ["x", "z"],
  "x-left-yz-right": ["x", ["y", "z"]]
};

window.onload = function () {
  const viewer = document.getElementById('viewer');
  const layoutSelect = document.getElementById('layoutSelect');
  const reloadButton = document.getElementById('reloadButton');

  Object.entries(layoutOptions).forEach(([key, val]) => {
    const opt = document.createElement("option");
    opt.value = key;
    const label = val.flat().map(k => docInfo[k].title).join(" + ");
    opt.textContent = label;
    layoutSelect.appendChild(opt);
  });

  function createPanel(key) {
    const container = document.createElement('div');
    container.className = 'panel';
    const title = document.createElement('h2');
    title.textContent = docInfo[key].title;
    const iframe = document.createElement('iframe');
    iframe.dataset.docKey = key;
    iframe.src = `${docInfo[key].src}?t=${Date.now()}`;
    container.appendChild(title);
    container.appendChild(iframe);
    return container;
  }

  function createLayout(layout) {
    viewer.innerHTML = "";
    const config = layoutOptions[layout];
    if (!config) return;
    config.forEach(item => {
      if (Array.isArray(item)) {
        const right = document.createElement("div");
        right.className = "panel vertical-split";
        item.forEach(subkey => right.appendChild(createPanel(subkey)));
        viewer.appendChild(right);
      } else {
        viewer.appendChild(createPanel(item));
      }
    });
  }

  layoutSelect.value = "x-left-z-right";
  createLayout(layoutSelect.value);
  layoutSelect.addEventListener("change", () => createLayout(layoutSelect.value));
  reloadButton.addEventListener("click", () => {
    document.querySelectorAll("iframe").forEach(iframe => {
      const key = iframe.dataset.docKey;
      iframe.src = `${docInfo[key].src}?t=${Date.now()}`;
    });
  });

  document.getElementById("addAnnotationLinks").addEventListener("click", async () => {
    await addAnnotationMarkers();
  });
};
