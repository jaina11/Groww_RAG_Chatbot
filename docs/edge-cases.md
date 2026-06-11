# Edge Cases

## 1. Advisory Queries → REFUSE
- "Should I invest in HDFC Mid Cap?"
- "Is this fund good for me?"
- "Which fund is better?"
- "Will this fund give good returns?"
- **Action:** Polite refusal + https://www.amfiindia.com/investor-corner/knowledge-center

## 2. Out-of-Scope Fund Queries → REFUSE
- Questions about any fund other than HDFC Mid Cap Direct Growth
- **Action:** "I only have information about HDFC Mid Cap Fund Direct Growth."

## 3. Performance/Returns Questions → REDIRECT
- "What are the 1yr/3yr/5yr returns?"
- **Action:** Return source URL only, no numbers. "Please check the latest returns at [source_url]"

## 4. Stale Data
- Data reflects last scrape date
- Footer always shows fetched_at date
- **Action:** Always include footer so user knows data freshness

## 5. Empty/Failed Scrape
- Groww page returns 403 or empty body
- **Action:** Log failure, keep previous index, do not serve stale chunks without footer date

## 6. PII in User Message
- User pastes PAN, Aadhaar, account number
- **Action:** Do not store, do not echo back, respond normally to the question only

## 7. Groq API Failure
- LLM call times out or returns error
- **Action:** Return fallback: "Unable to process your query right now. Please try again."

## 8. Vague Queries
- "Tell me about this fund" (no specific field)
- **Action:** Retrieve top chunk, answer what's available, cite source

## 9. ChromaDB Empty / Not Indexed
- Query before ingest has run
- **Action:** Return: "Data not yet indexed. Please try after the next scheduled update."

## 10. Forbidden Phrase Leakage
- LLM sneaks in "you should consider" etc.
- **Action:** Post-generation regex check → regenerate once → fallback to templated response