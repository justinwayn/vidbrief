// VidBrief MVP frontend — last 10 briefs in localStorage, one-click markdown copy.

const SAMPLE = `Sarah: Alright team, let's kick off the Q4 planning call. First item — the website relaunch. Mike, you were going to finish the homepage mockups. Where are we?
Mike: The mockups are done. I will send them to the design channel by Friday for review. We decided to go with the dark theme after the client feedback last week.
Sarah: Great, that's locked in then. Dark theme it is. Next — the pricing page. Lisa, can you draft the new tiers?
Lisa: Yes, I will draft three tiers — Starter, Pro, and Scale — and share them by Wednesday. I need the usage data from analytics first though.
Sarah: Mike, can you pull that for her?
Mike: Sure, I'll send Lisa the usage export today.
Sarah: Perfect. We also agreed to pause the mobile app until Q1, right?
Lisa: Right. We decided the web relaunch is the priority, mobile waits until January.
Sarah: Last thing — the holiday campaign. Someone needs to own the ad creative.
Mike: I'll take the lead on the holiday creative and have concepts ready next Monday.
Sarah: Awesome. Let's reconvene Friday to review the mockups.`;

const $ = id => document.getElementById(id);
const btn = $("summarize-btn");

function loadHistory() {
  try { return JSON.parse(localStorage.getItem("vidbrief_history") || "[]"); }
  catch { return []; }
}
function saveHistory(items) {
  localStorage.setItem("vidbrief_history", JSON.stringify(items.slice(0, 10)));
}
function renderHistory() {
  const items = loadHistory();
  const ul = $("history");
  ul.innerHTML = items.length ? "" : '<li class="muted">No briefs yet.</li>';
  items.forEach((it, i) => {
    const li = document.createElement("li");
    const when = new Date(it.when).toLocaleString();
    li.innerHTML = `<span><strong>${escapeHtml(it.title)}</strong> — ${it.actions} action items, ${it.decisions} decisions</span><span class="when">${when}</span>`;
    li.style.cursor = "pointer";
    li.onclick = () => restoreBrief(i);
    ul.appendChild(li);
  });
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

async function fetchEngine() {
  try {
    const r = await fetch("/api/health");
    const h = await r.json();
    $("engine-badge").textContent = h.ollama_available
      ? "engine: ollama (" + h.ollama_models[0] + ")"
      : "engine: heuristic (install Ollama for AI mode)";
  } catch { $("engine-badge").textContent = "engine: unknown"; }
}

async function summarize() {
  const transcript = $("transcript").value.trim();
  const title = $("title").value.trim() || "Meeting Brief";
  $("error").classList.add("hidden");
  if (transcript.length < 30) {
    showError("Paste at least a few sentences of transcript.");
    return;
  }
  btn.disabled = true; btn.textContent = "⏳ Generating…";
  try {
    const r = await fetch("/api/summarize", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({transcript, title}),
    });
    if (!r.ok) { showError((await r.json()).detail || "Summarization failed."); return; }
    const data = await r.json();
    showResult(data, title);
    $("engine-badge").textContent = "engine: " + data.engine;
  } catch (e) {
    showError("Could not reach the VidBrief server. Is it running?");
  } finally {
    btn.disabled = false; btn.textContent = "⚡ Generate Brief";
  }
}

function showError(msg) {
  const el = $("error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function showResult(data, title) {
  $("result").classList.remove("hidden");
  $("summary").textContent = data.summary || "—";
  renderList($("actions"), data.action_items, "No action items found.");
  renderList($("decisions"), data.key_decisions, "No key decisions found.");
  const items = loadHistory();
  items.unshift({title, when: Date.now(), actions: data.action_items.length,
                 decisions: data.key_decisions.length, data});
  saveHistory(items); renderHistory();
  $("copy-ok").classList.add("hidden");
  $("result").scrollIntoView({behavior: "smooth"});
}

function renderList(ul, items, empty) {
  ul.innerHTML = "";
  (items.length ? items : [empty]).forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  });
}

function restoreBrief(i) {
  const it = loadHistory()[i];
  if (!it) return;
  showResult(it.data, it.title);
}

async function copyMarkdown() {
  const transcript = $("transcript").value.trim();
  const title = $("title").value.trim() || "Meeting Brief";
  try {
    const r = await fetch("/api/markdown", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({transcript, title}),
    });
    const {markdown} = await r.json();
    await navigator.clipboard.writeText(markdown);
    $("copy-ok").classList.remove("hidden");
  } catch { showError("Copy failed — your browser blocked clipboard access."); }
}

$("sample-btn").onclick = () => { $("transcript").value = SAMPLE; };
btn.onclick = summarize;
$("copy-btn").onclick = copyMarkdown;

fetchEngine();
renderHistory();
