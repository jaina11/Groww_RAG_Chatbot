# RAG Architecture: Mutual Fund FAQ Assistant

> This document describes the retrieval-augmented generation (RAG) architecture for the facts-only mutual fund FAQ assistant. It prioritizes accuracy, provenance, and compliance over open-ended conversational ability.

---

## 1. Design Principles

| Principle | Implication for Architecture |
|-----------|------------------------------|
| Facts-only | Retrieval gates what the model may say; prompts and post-checks forbid advice and comparisons |
| Single canonical source per answer | Retrieval returns chunks tagged with one citation URL; generation is constrained to cite that URL only |
| Curated corpus | Ingestion is batch or scheduled from an allowlist of URLs; no arbitrary web crawling at query time |
| No PII | No user document upload path; chat payloads exclude identifiers; logs redact or omit sensitive fields |
| Accuracy over "intelligence" | Prefer abstention, refusal, or "see the indexed scheme page" over speculative answers |

---

## 2. Components Overview

- **Scheduler (GitHub Actions):** Runs daily at 09:15 IST (03:45 UTC) to execute the full ingest job. Supports `workflow_dispatch` for manual runs.
- **Scraping Service:** Reads URL registry, fetches each allowlisted page, persists raw HTML, passes content into normalize → chunk → embed → index.
- **Ingestion Pipeline:** Builds and refreshes the vector index and a parallel document registry.
- **Thread Store:** Persists conversation history per thread for multi-chat support without mixing contexts.
- **Query Router:** Classifies intent (factual FAQ vs advisory vs out-of-scope) before retrieval.
- **Retriever + Re-ranker:** Pulls top-k chunks from vector store, filters/re-ranks by scheme match, recency, and source type.
- **LLM Layer:** Generates short answer only from retrieved text, with fixed output schema (sentences + one link + footer date).
- **Post-guards:** Validate citation presence, sentence count, and forbidden patterns.

---

## 3. Corpus & Data Model

### 3.1 Scope — Current Corpus

**AMC:** HDFC Mutual Fund

| Scheme | URL |
|--------|-----|
| HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| HDFC Equity Fund Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC Focused Fund Direct Growth | https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |

> **Out of scope for now:** AMC PDFs (KIM, SID), standalone factsheet PDFs, AMFI/SEBI pages, and additional URLs. The ingestion pipeline should be built so PDFs and extra allowlist entries can be added later without redesign.
>
> **Note:** This phase uses Groww pages as the curated HTML corpus; expanding to primary AMC/AMFI/SEBI documents is a future corpus upgrade.

---

### 3.2 Document Metadata (per chunk)

| Field | Purpose |
|-------|---------|
| `source_url` | Canonical URL for citation (exactly one per assistant message) |
| `source_type` | e.g. `groww_scheme_page`; later `factsheet`, `kim`, `sid`, `amfi`, `sebi` |
| `scheme_id` / `scheme_name` | Tie chunks to a scheme; null for generic regulatory pages |
| `amc` | AMC identifier or name |
| `title` | Page or section title for debugging and UI tooltips |
| `fetched_at` | ISO date for "Last updated from sources" footer |
| `content_hash` | Detect content drift on re-crawl |

---

### 3.3 Chunking Strategy

- **HTML (Groww scheme pages):** Split on headings and logical sections; preserve tables as single units where possible so expense ratio / exit load rows stay intact.
- **PDF:** Not used in initial corpus; when added later, use page- or section-aware chunking.
- **Target chunk size:** ~300–450 tokens (tuned for BAAI/bge-small-en-v1.5, max 512 input tokens), with 10–15% overlap to preserve boundary context.
- **De-duplication:** Same URL + overlapping hash → keep one primary chunk or merge metadata.

---

### 3.4 Structured Fund Metrics

For fields like NAV, minimum SIP, AUM, expense ratio, and rating — use a **hybrid approach**:

| Layer | What it stores | Role |
|-------|---------------|------|
| Structured "facts" store | One record per scheme per scrape run with typed/labeled fields | Exact answers, filters, easy regression tests |
| Vector index (chunks) | Full normalized text/tables from the same page | Narrative context, exit load, benchmark, objectives |

**Recommended logical schema (per scheme, per snapshot):**

| Field | Storage Notes |
|-------|--------------|
| `scheme_id`, `scheme_name`, `amc` | From URL registry; stable keys |
| `source_url` | Groww page URL (citation) |
| `fetched_at` | ISO timestamp of scrape |
| `raw_content_hash` | Hash of raw HTML for traceability |
| `nav` | Number + currency (INR) + optional `as_of` date |
| `minimum_sip` | Number (INR) + frequency if stated |
| `fund_size` / `aum` | Number + unit (₹ Cr or raw string + parsed numeric) |
| `expense_ratio` | Percentage as number (e.g. 0.52 for 0.52% p.a.) + label (Direct/Regular) |
| `rating` | Raw label from page + `rating_kind` enum: `riskometer`, `analyst`, `unknown` |

> Use `null` for any field missing after parse; log parse warnings. Do not invent values.

---

## 4. Ingestion Pipeline

### 4.0 Scheduler and Scraping Service

**Scheduler — GitHub Actions**
- Runs every day at **09:15 IST** → cron: `45 3 * * *` (03:45 UTC; India has no DST)
- Workflow: `.github/workflows/ingest.yml`
- Steps in order: scrape → normalize → chunk + embed (local BAAI/bge-small-en-v1.5) → upsert to on-disk Chroma under `data/chroma/`
- Secrets: embedding uses local BGE (no API key); Chroma vectors live in local persist directory (`chromadb.PersistentClient`, default `data/chroma/`)
- Enable `workflow_dispatch` for manual triggers from the Actions tab
- Set `timeout-minutes: 30–60` so a hung scrape does not consume quota indefinitely
- Workflows may be retried; ingest must be safe to re-run (content_hash / upsert semantics)

**Scraping Service**
- Input: URL registry (allowlist only)
- For each URL: HTTP(S) GET, respect robots.txt, rate-limit between requests, use stable User-Agent identifying the assistant project
- Output: Raw HTML written to durable storage with timestamp; forward same payload to normalize stage
- On non-2xx / timeout / empty body: log, mark failure for that URL, continue with others
- Scope: Not a general-purpose crawler — only retrieves URLs explicitly listed in the registry

---

### 4.1 Pipeline Stages

1. **URL Registry** — Versioned list (YAML/JSON) of allowed URLs with tags: AMC, scheme, document type
2. **Fetch** — Executed on each scheduled or manual run; store raw HTML in object storage or disk
3. **Normalize** — Strip boilerplate (nav, footers) where safe; keep main content; PDF out of scope initially
4. **Chunk + Enrich** — Apply chunking rules; attach metadata
5. **Embed** — Embed with BAAI/bge-small-en-v1.5 (local inference via sentence-transformers, 384-dim)
6. **Index** — Upsert vectors and metadata into on-disk Chroma via PersistentClient
7. **Refresh** — Primary: daily at 09:15 IST via GitHub Actions; Secondary: `workflow_dispatch` or optional `POST /admin/reindex`

---

### 4.2 Failure Handling

- **Failed URL:** Log, alert, exclude from index until fixed; do not silently substitute off-allowlist sources
- **Partial or empty HTML parse:** Mark document quality flag; optionally exclude low-confidence chunks from retrieval

---

### 4.3 Vector Index — Local Chroma (PersistentClient)

**Product choice:** ChromaDB with `chromadb.PersistentClient` — vectors and metadata live under `data/chroma/` (configurable via `INGEST_CHROMA_DIR`).

**Ingest-time steps:**

1. **Client & path** — `PersistentClient(path=...)` pointing at `INGEST_CHROMA_DIR` (created if missing)
2. **Collection** — One logical collection per deployment (e.g. `mf_faq_chunks`) via `INGEST_CHROMA_COLLECTION`, created with `get_or_create_collection`; dimension: 384; distance: cosine
3. **Record shape:**
   - `id`: chunk_id (deterministic hash — idempotent upserts)
   - `embedding`: float vector length 384
   - `document`: chunk_text
   - `metadata`: `source_url`, `scheme_id`, `scheme_name`, `amc`, `source_type`, `fetched_at`, `chunk_index`, `section_title`, `run_id`
4. **Upsert strategy** — Upsert by chunk_id daily; skip write if `chunk_text_hash` unchanged
5. **Deletion** — If scheme removed from URL registry, delete all collection entries matching that `scheme_id`
6. **Registry / operator manifest** — Emit JSON per run: `embedding_model_id`, `run_id`, `collection_name`, `chroma_persist_path`, `chunk_count`, `updated_at`, `indexed_at`

**Query-time:**
- Same `PersistentClient` path as ingest
- Embed user query with same BGE model and query prefix `"Represent this sentence: "`
- `collection.query(query_embeddings=[...], n_results=k, where={...})` with optional `where` on `scheme_id` / `amc`

---

## 5. Retrieval Layer

> Implementation: `runtime/phase_5_retrieval/` — CLI: `python -m runtime.phase_5_retrieval "…"`

### 5.1 Query Preprocessing
- Light normalization: lowercase for matching; keep scheme names and tickers as entities
- Scheme resolution: constrain metadata filter `scheme_id` when confidence is high; otherwise retrieve broadly then re-rank

### 5.2 Retrieval Mechanics
1. **Dense retrieval:** Top-k (20–40) by cosine similarity in vector store
2. **Metadata filter:** Optional pre-filter by `scheme_id` or `amc` when resolved
3. **Re-ranking:** Cross-encoder or lightweight lexical re-rank on candidate chunks
4. **Merging:** If multiple chunks from same `source_url` score highly, merge text while keeping one citation URL

### 5.3 Source Selection for "Exactly One Link"
- **Primary rule:** Choose single highest-confidence chunk's `source_url` as citation
- **Conflict rule:** If chunks disagree, prefer newer `fetched_at` snapshot, or respond conservatively pointing to the scheme's allowlisted page URL

### 5.4 Performance-Related Questions
Per constraints: do not compute or compare returns. Answer with a link to the indexed scheme page only, plus minimal process language if present in corpus.

---

## 6. Generation Layer

> Implementation: `runtime/phase_6_generation/` — CLI: `python -m runtime.phase_6_generation "…"`

### 6.1 Prompting Strategy
- **System prompt:** Enforce facts-only, no recommendations, no comparisons, ≤3 sentences, exactly one URL from provided metadata, required footer line
- **Developer instructions:** "Use only the CONTEXT; if insufficient, say you cannot find it in the indexed sources and suggest the relevant allowlisted scheme URL"
- **Context packaging:** Pass retrieved chunk text with explicit `Source URL: ...` headers so the model does not invent links

### 6.2 Output Schema (Contract)
1. **Body:** ≤3 sentences, factual, no "you should invest"
2. **Citation:** Exactly one URL matching the selected `source_url`
3. **Footer:** `Last updated from sources: <date>` using `fetched_at` of cited source

### 6.3 Model Choice
- Prefer smaller instruction-tuned model with low temperature for determinism
- **LLM:** Groq chat API (model: `llama-3.1-8b-instant`, key: `GROQ_API_KEY`)
- **Embedding:** BAAI/bge-small-en-v1.5 (local) — independent of LLM provider

---

## 7. Refusal & Safety Layer

> Implementation: `runtime/phase_7_safety/` — CLI: `python -m runtime.phase_7_safety "…"` or `--route-only`

### 7.1 Advisory / Comparative Queries
**Detect:** "should I", "which is better", "best fund", "recommend", implicit ranking, personal situation ("I am 45…")

**Action:** No retrieval; return polite refusal + one educational link (AMFI/SEBI); no scheme-specific advice

### 7.2 Post-Generation Validation
Programmatic checks:
- Sentence count ≤3
- Exactly one HTTP(S) URL present and on allowlist
- Forbidden regex/keyword list: "invest in", "you should", "better than", "outperform", "guarantee"
- On failure: regenerate once with stricter prompt, or fall back to templated safe response with scheme's allowlisted URL

### 7.3 Privacy
- Do not request or store PAN, Aadhaar, account numbers, OTPs, email, phone
- "Paste your statement text" feature is out of scope — do not implement unless requirements change

---

## 8. Multi-Thread Chat Architecture

> Implementation: `runtime/phase_8_threads/` — CLI: `python -m runtime.phase_8_threads new-thread | say | history | context | list-threads`

### 8.1 Thread Model
- **Thread ID:** Opaque UUID per conversation
- **Ownership:** Associate with anonymous session or optional non-PII session key only
- **Storage:** Each message: `{ role, content, timestamp, optional retrieval_debug_id }`

### 8.2 Context Window Policy
- Use last N turns (4–6) for follow-up questions
- Optional retrieval query expansion using recent history — without injecting PII

### 8.3 Concurrency
- Stateless API servers; thread state in DB or durable KV
- Vector store read-only at query time; no cross-thread writes

### 8.4 UI Mapping
- Thread list + active thread; switching threads loads that thread's messages only

**SQLite thread/message store:** swap for Postgres in production (see Section 11). `THREAD_MAX_TURNS` controls last-N-turn window.

---

## 9. Application & API Layer

> Implementation: `runtime/phase_9_api/` — Run: `python -m runtime.phase_9_api`

### 9.1 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `POST /threads` | Create thread |
| `GET /threads/{id}/messages` | List messages |
| `POST /threads/{id}/messages` | User message → pipeline → assistant message |
| `POST /admin/reindex` | Protected re-ingestion trigger (optional) |

### 9.2 Response Payload
- `assistant_message` (user-visible)
- Optional `debug` (dev only): retrieved chunk IDs, scores — disabled in production

**UI:** Next.js in `web/` (`npm run dev`, `NEXT_PUBLIC_API_URL` → API origin). `RUNTIME_API_DEBUG=1` adds debug on post-message.

---

## 10. Observability & Quality

### 10.1 Logging
- Log query latency, retrieval count, router decision, refusal vs answer
- Do not log full message bodies if policy tightens

### 10.2 Evaluation (Offline)
- Golden set of ~50–100 Q&A pairs from corpus with expected source URL and allowed answer variants
- Metrics: citation URL exact match rate, grounding (answer supported by chunk), refusal precision/recall on advisory prompts

### 10.3 Drift
- Re-crawl alerts when `content_hash` changes for critical allowlisted URLs

---

## 11. Technology Stack

| Layer | Choice |
|-------|--------|
| Scheduled ingest | GitHub Actions (schedule + `workflow_dispatch`) |
| Vector DB | Chroma — `PersistentClient` on disk under `INGEST_CHROMA_DIR` |
| Embeddings | BAAI/bge-small-en-v1.5 via sentence-transformers (local, 384-dim, 512 max tokens) |
| LLM | Groq chat API (`GROQ_API_KEY`; model: `llama-3.1-8b-instant`) |
| Orchestration | LangChain/LlamaIndex or thin custom pipeline |
| UI | Next.js + Tailwind (dark theme) |
| Storage | Postgres for threads/messages; object store for raw fetches |

> Keep embedding model, chunking parameters, and Chroma collection dimension (384) **frozen** across index and query for reproducibility.

---

## 12. Known Limitations

| Limitation | Detail |
|------------|--------|
| Stale data | Answers reflect last crawl; footer date mitigates but does not eliminate staleness |
| HTML table / layout variance | Numeric FAQs sensitive to how Groww renders tables; PDF ingestion adds separate extraction risk |
| Narrow corpus | Only indexed schemes/pages are answerable; broad MF questions may need refusal + educational link |
| Router mistakes | Misclassified advisory queries could leak tone; combine router + post-guards |
| No real-time market data | By design |

---

## 13. Deliverables Mapping

| Deliverable | Where it lives |
|-------------|----------------|
| README setup, AMC/schemes, architecture, limitations | `docs/` + this file + `runtime/phase_5_retrieval/` through `runtime/phase_9_api/` |
| Disclaimer snippet | UI + optional system prompt reinforcement |
| Multi-thread chat | Section 8 + thread API in Section 9 |
| Facts-only + one citation + footer | Sections 5–7 and 6.2 |

---

## 14. Summary

The architecture is a **closed-book RAG system**: a curated, versioned corpus of allowlisted URLs (currently five Groww HDFC scheme pages, HTML only) is refreshed by a GitHub Actions schedule (09:15 IST) that runs:

```
scrape → normalize → chunk → embed → local Chroma vector upsert (data/chroma/)
```

At query time, a router and retriever (same on-disk collection; similarity + metadata filters) constrain what may be said. Prompts plus post-validation enforce how it is said — short, factual, one source link, and compliant refusal paths for non-factual or advisory requests. Multi-thread support is handled by durable per-thread history and conservative use of that history for retrieval query expansion only.