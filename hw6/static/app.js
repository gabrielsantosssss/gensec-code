// All server/LLM text is inserted with textContent (never innerHTML) to prevent XSS.
(function () {
  const form = document.getElementById("ask-form");
  const input = document.getElementById("query");
  const button = document.getElementById("submit");
  const status = document.getElementById("status");
  const answerSec = document.getElementById("answer-section");
  const answerEl = document.getElementById("answer");
  const sourcesSec = document.getElementById("sources-section");
  const sourcesEl = document.getElementById("sources");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    button.disabled = true;
    status.textContent = "Searching…";
    status.className = "";
    answerSec.hidden = true;
    sourcesSec.hidden = true;
    sourcesEl.replaceChildren();

    try {
      const resp = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        credentials: "same-origin",
        body: JSON.stringify({ query }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);

      answerEl.textContent = data.answer;
      answerSec.hidden = false;

      for (const s of data.sources || []) {
        const li = el("li");
        const head = el("div", "src-head");
        head.append(el("span", "src-name", `[${s.n}] ${s.source}`),
                    el("span", "src-meta", `chunk ${s.chunk} · similarity ${s.score}`));
        const details = el("details");
        details.append(el("summary", null, "Show snippet"), el("pre", "snippet", s.text));
        li.append(head, details);
        sourcesEl.append(li);
      }
      sourcesSec.hidden = sourcesEl.children.length === 0;
      status.textContent = "";
    } catch (err) {
      status.textContent = err.message;
      status.className = "error";
    } finally {
      button.disabled = false;
    }
  });
})();
