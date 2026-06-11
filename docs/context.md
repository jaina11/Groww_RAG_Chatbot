# Context.md — Cursor Knowledge Base

## What We're Building
A RAG-based FAQ chatbot for HDFC Mid Cap Fund Direct Growth (Groww data source).
Facts-only. No investment advice. Deployed on Render (backend) + Vercel (frontend).

## Current Phase
> Update this line as you progress through phases.
**Current: Frontend — Next.js**

Phases:
1. Project structure + GitHub setup
2. Scraping (Groww page → raw HTML)
3. Chunking + Embedding (BGE-small → ChromaDB)
4. FastAPI backend (retrieval + Groq LLM)
5. Next.js frontend (dark theme chat UI)
6. Deploy (Vercel + Render + GitHub Actions)

## Tech Stack
- Python 3.9, FastAPI, uvicorn
- ChromaDB (local persistent at `data/chroma/`)
- BAAI/bge-small-en-v1.5 via sentence-transformers
- Groq API (llama-3.1-8b-instant) — key in .env as GROQ_API_KEY
- Next.js 14, Tailwind CSS
- SQLite for chat sessions
- GitHub Actions for daily ingest (03:45 UTC = 09:15 IST)

## Source
- Single URL: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
- scheme_id: hdfc_mid_cap
- amc: HDFC

## Coding Rules for Cursor
1. Always read docs/ before writing any code
2. Create one file per phase, in the correct folder (ingest/ or runtime/)
3. All secrets via os.environ — never hardcode
4. Every function must have a docstring
5. Log to logs/ingest.log (ingest) and logs/runtime.log (runtime)
6. ChromaDB path always from env: CHROMA_DIR (default: data/chroma/)
7. Chunk size: 300-450 tokens, overlap 10%
8. Embedding model: BAAI/bge-small-en-v1.5 (384-dim) — never change this
9. LLM output: max 3 sentences, 1 citation URL, footer with fetched_at date
10. Post-generation check: sentence count, URL on allowlist, forbidden phrases

## What NOT To Do
- No investment advice in any response
- No comparisons between funds
- No PII storage or echoing
- No web crawling beyond the single allowlisted URL
- No PDFs in this phase
- No third-party blog/aggregator sources
- Do not change embedding model or ChromaDB dimension

## Environment Variables (.env)
```
GROQ_API_KEY=your_key_here
CHROMA_DIR=data/chroma/
CHROMA_COLLECTION=mf_faq_chunks
LOG_LEVEL=INFO
PORT=8000
```

## Key Files Reference
- docs/context.md — this file (project knowledge base)
- docs/problemStatement.md — what to build
- docs/rag-architecture.md — full architecture
- docs/edge-cases.md — all edge cases to handle
- data/chroma/ — vector index (committed to repo for Render deploy)
- .github/workflows/ingest.yml — daily scrape + index refresh