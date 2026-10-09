"""
VidBrief summarizer engine.

Strategy (zero-budget):
1. If a local Ollama server is reachable (localhost:11434) with any model,
   use it for high-quality extraction (no paid APIs, runs on the user's machine).
2. Otherwise fall back to a deterministic heuristic extractor — pure Python,
   no dependencies, works everywhere.

Both paths return the same shape:
{
    "summary": str,              # 2-4 sentence overview
    "action_items": [str],       # list of action items
    "key_decisions": [str],      # list of decisions
    "engine": "ollama:<model>" | "heuristic"
}
"""
import json
import re
import urllib.request
from collections import Counter

OLLAMA_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Ollama path
# ---------------------------------------------------------------------------

def _ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _ollama_generate(model, prompt, timeout=90):
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 800},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data.get("response", "")


OLLAMA_PROMPT = """You are VidBrief, a meeting summarizer. Read the meeting transcript below and respond ONLY with valid JSON in this exact format:
{{"summary": "2-4 sentence overview of the meeting", "action_items": ["item 1", "item 2"], "key_decisions": ["decision 1", "decision 2"]}}
Rules: action_items are concrete tasks with an owner when mentioned. key_decisions are explicit decisions or agreements. Keep items short. If there are no action items or decisions, use empty arrays.

TRANSCRIPT:
{transcript}
"""


def summarize_with_ollama(transcript):
    models = _ollama_models()
    if not models:
        return None
    # Prefer smaller/faster models the user already has
    preferred = ["qwen3.5", "qwen3.5:latest", "llama3.2", "llama3.2:latest",
                 "gemma4", "qwen3", "llama3.1"]
    model = next((m for m in preferred if m in models), models[0])
    text = _ollama_generate(model, OLLAMA_PROMPT.format(transcript=transcript[:6000]))
    # Extract JSON from the response (models sometimes add chatter)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return {
            "summary": str(data.get("summary", "")),
            "action_items": [str(x) for x in data.get("action_items", [])][:15],
            "key_decisions": [str(x) for x in data.get("key_decisions", [])][:15],
            "engine": f"ollama:{model}",
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Heuristic path (pure Python, no deps)
# ---------------------------------------------------------------------------

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

ACTION_VERBS = re.compile(
    r"\b(will|shall|must|need to|needs to|has to|have to|should|going to|"
    r"assign|task|todo|follow up|follow-up|send|circle back|draft|prepare|"
    r"schedule|book|call|email|review|update|finish|complete|deliver|share|"
    r"check|confirm|get back|reach out|look into|investigate|own|take the lead)\b",
    re.IGNORECASE)

DECISION_PAT = re.compile(
    r"\b(decided|decision|agreed|agreement|concluded|final call|we'?ll go with|"
    r"approved|sign ?off|green ?light|locked in|settled on|going with|"
    r"consensus|resolved|the plan is|moving forward with)\b",
    re.IGNORECASE)

OWNER_PAT = re.compile(r"\b([A-Z][a-z]{2,15})\s+(will|shall|is going to|agreed to|"
                       r"volunteered to|took|owns|will own)\b")

FILLER = re.compile(r"\b(um+|uh+|like|you know|actually|basically|so+|well)\b", re.IGNORECASE)

STOPWORDS = set("""a an the and or but if then else when while of at by for with about
into through during before after above below to from up down in out on off over
under again further once here there all any both each few more most other some
such no nor not only own same so than too very can will just don should now
is are was were be been being have has had having do does did doing would could
ought i me my we our you your he him his she her it its they them their this
that these those am as""".split())


def _clean(s):
    s = FILLER.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) > 12]


def _score_sentences(sentences):
    words = Counter()
    for s in sentences:
        for w in re.findall(r"[a-z]{3,}", s.lower()):
            if w not in STOPWORDS:
                words[w] += 1
    scored = []
    for s in sentences:
        toks = [w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in STOPWORDS]
        if not toks:
            continue
        score = sum(words[w] for w in toks) / (len(toks) ** 0.6)
        scored.append((score, s))
    scored.sort(reverse=True)
    return [s for _, s in scored]


def summarize_heuristic(transcript):
    transcript = _clean(transcript)
    sentences = _sentences(transcript)
    if not sentences:
        return {"summary": "No readable content found in the transcript.",
                "action_items": [], "key_decisions": [], "engine": "heuristic"}

    action_items, key_decisions = [], []
    seen_norm = set()
    for s in sentences:
        cs = _clean(s)
        if len(cs) < 20 or len(cs) >= 280:
            continue
        norm = cs.lower()
        if norm in seen_norm:
            continue
        # skip pure questions that carry no action
        if cs.endswith("?") and not ACTION_VERBS.search(cs):
            continue
        is_action = bool(ACTION_VERBS.search(cs))
        is_decision = bool(DECISION_PAT.search(cs))
        if not (is_action or is_decision):
            continue
        seen_norm.add(norm)
        cap = cs[0].upper() + cs[1:]
        if is_action:
            action_items.append(cap)
        if is_decision:
            key_decisions.append(cap)

    ranked = _score_sentences(sentences)
    # summary: top 3 scored sentences, kept in original order
    top = set(ranked[:3])
    ordered = [s for s in sentences if s in top]
    summary = " ".join(_clean(s) for s in ordered[:3])

    return {
        "summary": summary,
        "action_items": action_items[:12],
        "key_decisions": key_decisions[:12],
        "engine": "heuristic",
    }


def summarize(transcript):
    """Public entry: Ollama first, heuristic fallback."""
    transcript = (transcript or "").strip()
    if len(transcript) < 30:
        return {"summary": "", "action_items": [], "key_decisions": [],
                "engine": "none", "error": "Transcript too short — paste at least a few sentences."}
    try:
        result = summarize_with_ollama(transcript)
        if result and (result["summary"] or result["action_items"] or result["key_decisions"]):
            return result
    except Exception:
        pass
    return summarize_heuristic(transcript)


def to_markdown(result, title="Meeting Brief"):
    lines = [f"# {title}", "", "## Summary", "", result["summary"] or "_No summary._", ""]
    lines += ["## Action Items", ""]
    if result["action_items"]:
        lines += [f"- [ ] {a}" for a in result["action_items"]]
    else:
        lines += ["_None found._"]
    lines += ["", "## Key Decisions", ""]
    if result["key_decisions"]:
        lines += [f"- {d}" for d in result["key_decisions"]]
    else:
        lines += ["_None found._"]
    lines += ["", f"_Generated by VidBrief ({result['engine']})_"]
    return "\n".join(lines)
