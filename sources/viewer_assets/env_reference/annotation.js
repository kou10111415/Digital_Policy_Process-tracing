export async function addAnnotationMarkers() {
  const xIframe = Array.from(document.querySelectorAll("iframe")).find(f => f.dataset.docKey === "x");
  if (!xIframe) return;

  const xDoc = xIframe.contentDocument;
  const res = await fetch("./annotations.json");
  const annotations = await res.json();

  for (const anno of annotations) {
    const rangeMatch = anno.id.match(/^u(\d+)seg(\d+)-seg(\d+)$/);
    const singleMatch = anno.id.match(/^u(\d+)seg(\d+)$/);

    if (!rangeMatch && !singleMatch) continue;

    const uId = rangeMatch ? rangeMatch[1] : singleMatch[1];
    const startSeg = rangeMatch ? parseInt(rangeMatch[2]) : parseInt(singleMatch[2]);
    const endSeg = rangeMatch ? parseInt(rangeMatch[3]) : startSeg;

    const uEl = xDoc.querySelector('[id="u' + uId + '"]');
    if (!uEl) continue;

    for (let segNo = startSeg; segNo <= endSeg; segNo++) {
      const segEl = uEl.querySelector('[id="seg' + segNo + '"]');
      if (!segEl) continue;

      const marker = xDoc.createElement("span");
      marker.dataset.draft = JSON.stringify(anno.linkedDraft);
      marker.dataset.proposal = JSON.stringify(anno.linkedProposal);
      marker.dataset.uSegId = anno.id;

      marker.style.background = "rgba(255, 200, 0, 0.3)";
      marker.style.cursor = "pointer";
      marker.style.textDecoration = "underline";
      marker.style.textDecorationThickness = "0.25em";
      marker.style.textDecorationColor = "orange";
      marker.style.textUnderlineOffset = "0.1em";

      marker.addEventListener("click", e => {
        e.preventDefault();
        showAnnotationDetails(
          JSON.parse(marker.dataset.draft),
          JSON.parse(marker.dataset.proposal),
          marker.dataset.uSegId
        );
      });

      const range = xDoc.createRange();
      range.selectNodeContents(segEl);
      try {
        range.surroundContents(marker);
      } catch (e) {
        console.warn(`⚠️ Could not surround seg${segNo} in u${uId}`, e);
        continue;
      }
    }
  }
}

async function showAnnotationDetails(draftInfo, proposalInfo, uSegId) {
  const viewer = document.getElementById("viewer");
  const panel = document.createElement("div");
  panel.className = "panel vertical-split";
  // 💡 ここで h2 を追加
  const h2 = document.createElement("h2");
  h2.textContent = "発言と関連文書";
  panel.appendChild(h2);

  // 議事録内の seg を抽出
  const xIframe = Array.from(document.querySelectorAll("iframe")).find(f => f.dataset.docKey === "x");
  const xDoc = xIframe?.contentDocument;
  let meetingContent = document.createElement("div");
  meetingContent.innerHTML = "<h3 style=\"margin-left: 2em;\">議事録</h3><p>未取得</p>";
  console.log(xDoc);
  console.log(uSegId);

  if (xDoc && uSegId) {
    const uMatch = uSegId.match(/^u(\d+)seg(\d+)$/);
    console.log("1")
    if (uMatch) {
      console.log("2")
      const uEl = xDoc.querySelector(`#u${uMatch[1]}`);
      const segEl = uEl?.querySelector(`#seg${uMatch[2]}`);
      if (segEl) {
        const cloned = segEl.cloneNode(true);
        // span.marker を除去（または span を unwrap）
        const spans = cloned.querySelectorAll("span");
        spans.forEach(span => {
          const parent = span.parentNode;
          while (span.firstChild) {
            parent.insertBefore(span.firstChild, span);
          }
          parent.removeChild(span);
        });      
        const wrapper = document.createElement("div");
        wrapper.innerHTML = `<h3 style="margin-left: 2em;">議事録</h3><div style="padding:1em;"></div>`;
        wrapper.querySelector("div").appendChild(cloned);
        meetingContent = wrapper;

        // 発言者情報の抽出
        const note = uEl.querySelector("tei-note");
        if (note) {
          const speakerInfo = getSpeakerInfoFromU(xDoc, uEl);
          const speakerDiv = document.createElement("div");
          speakerDiv.style.fontSize = "0.9em";
          speakerDiv.style.padding = "0.5em 1em";
          speakerDiv.style.background = "#f9f9f9";
          speakerDiv.innerHTML = `<strong>発言者:</strong> ${speakerInfo}`;
          wrapper.insertBefore(speakerDiv, wrapper.children[1]);
        }
      }
    }
  }

  // 素案・案のセグメント処理
  const draft = await (draftInfo.target.includes("-")
    ? createContentSpan(draftInfo.file, "計画素案", draftInfo.target)
    : createContent(draftInfo.file, "計画素案", draftInfo.target));

  const proposal = await (proposalInfo.target.includes("-")
    ? createContentSpan(proposalInfo.file, "計画案", proposalInfo.target)
    : createContent(proposalInfo.file, "計画案", proposalInfo.target));

  // 描画
  panel.appendChild(meetingContent);
  panel.appendChild(draft);
  panel.appendChild(proposal);

  const panels = viewer.querySelectorAll(".panel");
  if (panels.length >= 2) {
    viewer.replaceChild(panel, panels[1]);
  } else {
    viewer.appendChild(panel);
  }
}

function getSpeakerInfoFromU(xDoc, uEl) {
  const who = uEl.getAttribute("who")?.replace(/^#/, "");
  const noteEl = uEl.querySelector("note");

  let displayName = "(名称不明)";

  if (who) {
    const person = xDoc.querySelector(`#${who}`);
    if (person) {
      const surname = person.querySelector("tei-persname > tei-surname")?.textContent || "";
      const forename = person.querySelector("tei-persname > tei-forename")?.textContent || "";
      const org = person.querySelector("tei-affiliation > tei-orgname")?.textContent || "";
      const role = person.querySelector("tei-affiliation > tei-rolename")?.textContent || "";

      const fullName = `${surname}${forename}`.trim();
      const extra = `${org} ${role}`.trim();
      return extra ? `○${fullName}（${extra}）` : `○${fullName}`;
    }
  }

  // fallback
  const fallback = noteEl?.textContent?.trim();
  return fallback || "(名称不明)";
}

async function createContent(file, label, match) {
  const res = await fetch(file);
  const html = await res.text();
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const [pageno, lineno] = match.match(/p(\d+)l(\d+)/).slice(1);
  const el = doc.querySelector(`[data-pageno='${pageno}'][data-lineno='${lineno}']`);
  const wrap = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = label;
  title.style.marginLeft = "2em";
  const body = document.createElement("div");
  body.style.padding = "1em";
  body.innerHTML = el ? el.outerHTML : "<p>該当箇所なし</p>";
  wrap.appendChild(title);
  wrap.appendChild(body);
  return wrap;
}

async function createContentSpan(file, label, range) {
  const res = await fetch(file);
  const html = await res.text();
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  
  const [start, end] = range.split("-");
  const [pStart, lStart] = start.match(/p(\d+)l(\d+)/).slice(1).map(Number);
  const [pEnd, lEnd] = end.match(/p(\d+)l(\d+)/).slice(1).map(Number);
  console.log("📘 pStart, lStart:", pStart, lStart, "pEnd, lEnd:", pEnd, lEnd);

  const all = Array.from(doc.querySelectorAll("[data-pageno][data-lineno]"));
  const filtered = all.filter(el => {
    const p = parseInt(el.getAttribute("data-pageno"));
    const l = parseInt(el.getAttribute("data-lineno"));
    const inStart = p > pStart || (p === pStart && l >= lStart);
    const inEnd = p < pEnd || (p === pEnd && l <= lEnd);
    return inStart && inEnd;
  });

  const wrap = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = label;
  title.style.marginLeft = "2em";
  const body = document.createElement("div");
  body.style.padding = "1em";

  if (filtered.length > 0) {
    filtered.forEach(el => body.appendChild(el.cloneNode(true)));
  } else {
    body.innerHTML = "<p>範囲が見つかりませんでした</p>";
  }

  wrap.appendChild(title);
  wrap.appendChild(body);
  return wrap;
}
