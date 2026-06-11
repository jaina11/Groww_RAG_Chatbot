"""Build Groq chat prompts from retrieved context."""

from __future__ import annotations

from typing import List, Sequence

from runtime.phase_5_retrieval.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant.
Rules:
- Answer ONLY using the provided CONTEXT. Do not invent facts or URLs.
- No investment advice, recommendations, rankings, or fund comparisons.
- Use at most 3 short factual sentences in the body.
- Include exactly one citation URL on its own line (must match a Source URL from CONTEXT).
- End with this exact footer format on its own line: Last updated from sources: <date>
- Use the fetched_at date from the cited chunk for the footer date (YYYY-MM-DD).
- If CONTEXT is insufficient, say you cannot find it in the indexed sources and cite the most relevant Source URL from CONTEXT.
"""

STRICT_ADDENDUM = """CRITICAL: Your previous answer failed compliance checks.
Reply again with at most 3 short sentences, exactly one allowlisted URL, the required footer, and no advisory language.
"""


def _format_fetched_at(fetched_at: str) -> str:
    """
    Reduce an ISO timestamp to a YYYY-MM-DD footer date.
    """
    return fetched_at[:10] if fetched_at else "unknown"


def build_context_block(chunks: Sequence[RetrievedChunk]) -> str:
    """
    Package retrieved chunks with explicit source headers for the model.
    """
    sections: List[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source_url = str(chunk.metadata.get("source_url", ""))
        fetched_at = str(chunk.metadata.get("fetched_at", ""))
        scheme_name = str(chunk.metadata.get("scheme_name", ""))
        sections.append(
            "\n".join(
                [
                    f"### Chunk {index}",
                    f"Source URL: {source_url}",
                    f"Scheme: {scheme_name}",
                    f"fetched_at: {fetched_at}",
                    chunk.text,
                ]
            )
        )
    return "\n\n".join(sections)


def build_messages(
    query: str,
    chunks: Sequence[RetrievedChunk],
    citation_url: str,
    fetched_at: str,
    strict: bool = False,
) -> List[dict]:
    """
    Build Groq chat messages for a user query and retrieved context.
    """
    footer_date = _format_fetched_at(fetched_at)
    context = build_context_block(chunks)
    system_prompt = SYSTEM_PROMPT
    if strict:
        system_prompt = f"{SYSTEM_PROMPT}\n{STRICT_ADDENDUM}"

    user_prompt = (
        f"QUESTION: {query}\n\n"
        f"PRIMARY CITATION URL: {citation_url}\n"
        f"PRIMARY fetched_at: {footer_date}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "Write the final answer now."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
