# VidBrief MVP

Instant AI meeting summaries & action item extractor. 100% free — no accounts, no cloud, no paid APIs.

## What it does
- Paste a meeting transcript (Google Vids / Meet captions / notes)
- Extracts **Action Items** and **Key Decisions**
- Generates a clean **markdown summary card** with one-click copy
- Stores your **last 10 briefs** in browser localStorage

## Engine
1. **Ollama (AI mode)** — if a local Ollama server is running (`localhost:11434`) with any model, VidBrief uses it for high-quality extraction. This is how Justin's laptop runs it (he has qwen3.5 + llama3.2).
2. **Heuristic fallback** — pure-Python extractive summarizer (action verbs, decision patterns, TF-scored sentences). Works anywhere, no dependencies.

The active engine is shown in the UI badge.

## Run it

```bash
cd ~/workspace/agent-army/builds/prod_1790955630/app
# one-time setup (venv already created; system pip is Debian-managed)
./venv/bin/pip install -r requirements.txt
# run
./venv/bin/python main.py        # or: ./venv/bin/uvicorn main:app --port 8091
```

Then open **http://localhost:8091**

## API
- `POST /api/summarize` → `{transcript, title}` → `{summary, action_items, key_decisions, engine}`
- `POST /api/markdown` → same input → `{markdown, engine}` (copy-ready)
- `GET /api/health` → `{ok, ollama_available, ollama_models}`

## Zero-budget compliance
- ✅ No paid APIs (OpenAI key removed from the stack)
- ✅ No cloud services (runs locally)
- ✅ No ad spend
- ✅ Optional Ollama is free and local

## Still needed before shipping
- [ ] Chrome Extension (Manifest V3) to grab Google Vids transcripts in one click — currently transcripts are pasted manually
- [ ] Google OAuth for direct Google Workspace/Vids integration
- [ ] Landing page with email capture (copy is in the product brief)
- [ ] 10 beta users to validate summary quality
- [ ] Monetization: $12/mo/seat with custom branding (Stripe integration)
