"""HTML normalization: strip boilerplate and extract structured text."""

from __future__ import annotations

import re
from typing import List, Set

from bs4 import BeautifulSoup, Tag

BOILERPLATE_TAGS = {
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "iframe",
    "svg",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    "link",
    "meta",
}

BOILERPLATE_CLASS_PATTERNS = re.compile(
    r"(footer|navbar|nav-bar|navigation|cookie|webengage|freshchat|sidebar|breadcrumb)",
    re.IGNORECASE,
)

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
TEXT_BLOCK_TAGS = {"div", "p", "span"}
FACT_KEYWORD_PATTERN = re.compile(
    r"expense\s*ratio|exit\s*load|minimum|sip|lumpsum|lock-in",
    re.IGNORECASE,
)
MIN_FACT_BLOCK_LEN = 3
MAX_FACT_BLOCK_LEN = 600


def _is_boilerplate_element(element: Tag) -> bool:
    """
    Return True when an element looks like site chrome rather than fund content.
    """
    attrs = element.attrs or {}
    element_id = str(attrs.get("id", "") or "")
    classes = attrs.get("class", []) or []
    if isinstance(classes, str):
        classes = [classes]
    class_values = " ".join(classes)
    haystack = f"{element_id} {class_values}"
    if BOILERPLATE_CLASS_PATTERNS.search(haystack):
        return True
    role = str(attrs.get("role", "") or "").lower()
    return role in {"navigation", "banner", "contentinfo", "complementary"}


def _remove_boilerplate(soup: BeautifulSoup) -> None:
    """
    Remove scripts, navigation, footers, and other non-content elements in place.
    """
    if soup.head:
        soup.head.decompose()

    for tag_name in BOILERPLATE_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()

    for element in list(soup.find_all(True)):
        if isinstance(element, Tag) and _is_boilerplate_element(element):
            element.decompose()


def _table_to_text(table: Tag) -> str:
    """
    Convert an HTML table into plain-text rows, keeping row values together.
    """
    rows: List[str] = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _normalize_text_key(text: str) -> str:
    """
    Normalize text for deduplication comparisons.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def _element_has_fact_signal(text: str) -> bool:
    """
    Return True when a text block likely contains key fund facts.

    Matches blocks with currency, percentages, or fund-fact keywords plus digits.
    """
    if len(text) < MIN_FACT_BLOCK_LEN or len(text) > MAX_FACT_BLOCK_LEN:
        return False

    has_keyword = bool(FACT_KEYWORD_PATTERN.search(text))
    has_rupee = "₹" in text
    has_percent = "%" in text
    has_digit = any(char.isdigit() for char in text)

    if has_rupee or has_percent:
        return True
    if has_keyword and has_digit:
        return True
    return False


def _build_fact_text_index(root: Tag) -> dict[str, str]:
    """
    Collect fund-fact strings from div/p/span blocks, preferring richer parent text.

    Drops shorter texts that are already contained in a longer matching block so
    labels like "Expense ratio 0.73%" are kept instead of bare "0.73%".
    """
    candidates: List[str] = []
    for element in root.find_all(TEXT_BLOCK_TAGS):
        if element.find_parent("table") is not None:
            continue
        text = element.get_text(" ", strip=True)
        if _element_has_fact_signal(text):
            candidates.append(text)

    kept_keys: Set[str] = set()
    fact_index: dict[str, str] = {}
    for text in sorted(set(candidates), key=len, reverse=True):
        key = _normalize_text_key(text)
        if any(key in existing for existing in kept_keys):
            continue
        fact_index[key] = text
        kept_keys.add(key)
    return fact_index


def _collect_blocks(root: Tag) -> List[str]:
    """
    Collect content blocks in document order from headings, tables, and fact text.
    """
    blocks: List[str] = []
    fact_index = _build_fact_text_index(root)
    added_fact_keys: Set[str] = set()
    seen_tables: Set[int] = set()

    for element in root.descendants:
        if not isinstance(element, Tag):
            continue

        if element.name in HEADING_TAGS:
            heading = element.get_text(" ", strip=True)
            if heading:
                blocks.append(f"## {heading}")
            continue

        if element.name == "table":
            table_id = id(element)
            if table_id in seen_tables:
                continue
            seen_tables.add(table_id)
            table_text = _table_to_text(element)
            if table_text:
                blocks.append(table_text)
            continue

        if element.name not in TEXT_BLOCK_TAGS:
            continue
        if element.find_parent("table") is not None:
            continue

        text = element.get_text(" ", strip=True)
        key = _normalize_text_key(text)
        if key not in fact_index or key in added_fact_keys:
            continue
        added_fact_keys.add(key)
        blocks.append(fact_index[key])

    if blocks:
        return blocks

    body_text = root.get_text("\n", strip=True)
    return [body_text] if body_text else []


def _group_blocks_into_sections(blocks: List[str]) -> List[str]:
    """
    Group heading blocks with the content that follows each heading.
    """
    sections: List[str] = []
    current_heading = ""
    current_lines: List[str] = []

    def flush_section() -> None:
        """Append the accumulated section when it has body text."""
        nonlocal current_heading, current_lines
        body = "\n".join(line for line in current_lines if line.strip())
        if not body and not current_heading:
            return
        if current_heading and body:
            sections.append(f"{current_heading}\n{body}")
        elif current_heading:
            sections.append(current_heading)
        elif body:
            sections.append(body)
        current_heading = ""
        current_lines = []

    for block in blocks:
        if block.startswith("## "):
            flush_section()
            current_heading = block[3:].strip()
            continue
        current_lines.append(block)

    flush_section()
    return sections


def clean_html(html: str) -> str:
    """
    Strip nav, footer, scripts, and other boilerplate from raw Groww HTML.

    Returns normalized plain text with section headings, tables, and key fund
    facts from div/p/span blocks preserved.
    """
    soup = BeautifulSoup(html, "html.parser")
    _remove_boilerplate(soup)

    root = soup.body or soup
    blocks = _collect_blocks(root)
    sections = _group_blocks_into_sections(blocks)

    if not sections:
        fallback = root.get_text("\n", strip=True)
        return fallback

    deduped: List[str] = []
    seen = set()
    for section in sections:
        key = re.sub(r"\s+", " ", section).strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(section.strip())

    return "\n\n".join(deduped)
