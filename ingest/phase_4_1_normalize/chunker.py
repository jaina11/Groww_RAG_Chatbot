"""Token-budget chunking with overlap for normalized fund text."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List

DEFAULT_CHUNK_SIZE_TOKENS = 400
DEFAULT_CHUNK_OVERLAP_RATIO = 0.10

_WORD_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class TextChunk:
    """One chunk of normalized text with ingest metadata."""

    text: str
    metadata: Dict[str, object]


def _estimate_word_tokens(word: str) -> int:
    """
    Approximate subword token count for English text (BGE-sized chunks).
    """
    return max(1, (len(word) + 3) // 4)


def count_tokens(text: str) -> int:
    """
    Estimate the number of embedding-model tokens in a text string.
    """
    words = _WORD_PATTERN.findall(text)
    if not words:
        return 0
    return sum(_estimate_word_tokens(word) for word in words)


def _split_words(text: str) -> List[str]:
    """
    Split text into whitespace-delimited words while keeping punctuation attached.
    """
    return _WORD_PATTERN.findall(text)


def _join_words(words: List[str]) -> str:
    """
    Rejoin chunked words into a single string.
    """
    return " ".join(words).strip()


def _chunk_words(
    words: List[str],
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> List[str]:
    """
    Split a word sequence into token-budget chunks with fixed overlap.
    """
    if not words:
        return []

    chunks: List[str] = []
    start = 0
    total_words = len(words)

    while start < total_words:
        token_budget = 0
        end = start
        while end < total_words:
            next_tokens = _estimate_word_tokens(words[end])
            if token_budget + next_tokens > chunk_size_tokens and end > start:
                break
            token_budget += next_tokens
            end += 1
            if token_budget >= chunk_size_tokens:
                break

        chunk_text_value = _join_words(words[start:end])
        if chunk_text_value:
            chunks.append(chunk_text_value)

        if end >= total_words:
            break

        if overlap_tokens <= 0:
            start = end
            continue

        overlap_used = 0
        overlap_start = end
        while overlap_start > start and overlap_used < overlap_tokens:
            overlap_start -= 1
            overlap_used += _estimate_word_tokens(words[overlap_start])

        start = max(overlap_start, start + 1)

    return chunks


def chunk_sections(
    sections: List[str],
    chunk_size_tokens: int,
    overlap_ratio: float,
) -> List[str]:
    """
    Chunk logical sections, keeping tables intact when they fit the token budget.

    Sections larger than the budget are split with overlap; smaller sections are
    merged greedily until the budget is reached.
    """
    overlap_tokens = int(chunk_size_tokens * overlap_ratio)
    packed_sections: List[str] = []
    buffer_lines: List[str] = []
    buffer_tokens = 0

    def flush_buffer() -> None:
        """Emit the current buffered section group as one logical block."""
        nonlocal buffer_lines, buffer_tokens
        if buffer_lines:
            packed_sections.append("\n\n".join(buffer_lines))
            buffer_lines = []
            buffer_tokens = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        section_tokens = count_tokens(section)
        if section_tokens > chunk_size_tokens:
            flush_buffer()
            packed_sections.append(section)
            continue

        if buffer_tokens + section_tokens > chunk_size_tokens and buffer_lines:
            flush_buffer()

        buffer_lines.append(section)
        buffer_tokens += section_tokens

    flush_buffer()

    output: List[str] = []
    for block in packed_sections:
        block_tokens = count_tokens(block)
        if block_tokens <= chunk_size_tokens:
            output.append(block)
            continue
        words = _split_words(block)
        output.extend(_chunk_words(words, chunk_size_tokens, overlap_tokens))

    return [chunk for chunk in output if chunk.strip()]


def chunk_text(
    text: str,
    chunk_size_tokens: int | None = None,
    overlap_ratio: float | None = None,
) -> List[str]:
    """
    Chunk normalized plain text using the configured token budget and overlap.
    """
    chunk_size = chunk_size_tokens or int(
        os.environ.get("CHUNK_SIZE_TOKENS", DEFAULT_CHUNK_SIZE_TOKENS)
    )
    overlap = overlap_ratio
    if overlap is None:
        overlap = float(os.environ.get("CHUNK_OVERLAP_RATIO", DEFAULT_CHUNK_OVERLAP_RATIO))

    sections = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not sections:
        return []
    return chunk_sections(sections, chunk_size, overlap)


def build_chunks(
    text: str,
    source_url: str,
    scheme_id: str,
    scheme_name: str,
    amc: str,
    fetched_at: str,
    chunk_size_tokens: int | None = None,
    overlap_ratio: float | None = None,
) -> List[TextChunk]:
    """
    Normalize text into chunks, attaching required metadata on each chunk.
    """
    chunk_texts = chunk_text(
        text,
        chunk_size_tokens=chunk_size_tokens,
        overlap_ratio=overlap_ratio,
    )
    chunks: List[TextChunk] = []
    for index, chunk_body in enumerate(chunk_texts):
        chunks.append(
            TextChunk(
                text=chunk_body,
                metadata={
                    "source_url": source_url,
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "amc": amc,
                    "fetched_at": fetched_at,
                    "chunk_index": index,
                },
            )
        )
    return chunks
