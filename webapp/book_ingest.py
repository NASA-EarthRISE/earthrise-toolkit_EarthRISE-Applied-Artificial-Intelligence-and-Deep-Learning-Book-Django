# webapp/book_ingest.py
"""
Convert a Chapter's html_content into a list of embedding-ready chunks.

Hierarchy:
  parent  — one per section (~1 500 words); stored for context expansion
  child   — ~400 words with 80-word overlap within each parent section
  code    — standalone code blocks extracted from <pre><code> elements

Each chunk dict: {id, text, metadata}

Metadata fields
  chapter     : chapter slug
  chapter_title: chapter human title
  section     : heading text for the section (empty for intro)
  chunk_type  : "parent" | "child" | "code"
  parent_id   : numeric id of the parent chunk (child/code chunks only)
  chunk_idx   : sequential integer across all chunks for this chapter
  is_global   : True  (book content is always globally available to the store)
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup, NavigableString

# Approximate word counts
PARENT_WORDS = 1500   # max words per parent (section) chunk
CHILD_WORDS  = 400    # target words per child chunk
CHILD_OVERLAP = 80    # word overlap between consecutive child chunks


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_chapter(slug: str, title: str, html_content: str) -> List[Dict[str, Any]]:
    """
    Parse html_content and return a flat list of chunk dicts ready for upsert.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script/style noise
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    sections = _split_into_sections(soup)
    docs: List[Dict[str, Any]] = []
    chunk_idx = 0
    parent_counter = 0

    for section_heading, elements in sections:
        # ── Extract code blocks first (before stripping them from text) ──────
        code_blocks = []
        for elem in elements:
            for pre in elem.find_all("pre") if hasattr(elem, "find_all") else []:
                code_text = pre.get_text().strip()
                if code_text:
                    code_blocks.append(code_text)

        # ── Plain text of the section (without code) ────────────────────────
        section_text_parts = []
        for elem in elements:
            if isinstance(elem, NavigableString):
                section_text_parts.append(str(elem).strip())
            elif hasattr(elem, "get_text"):
                # Skip pure code elements to avoid duplication
                clone = BeautifulSoup(str(elem), "html.parser")
                for pre in clone.find_all("pre"):
                    pre.decompose()
                text = clone.get_text(" ", strip=True)
                if text:
                    section_text_parts.append(text)

        section_text = " ".join(section_text_parts).strip()
        if not section_text and not code_blocks:
            continue

        parent_id = parent_counter
        parent_counter += 1

        base_meta = {
            "chapter":        slug,
            "chapter_title":  title,
            "section":        section_heading,
            "is_global":      True,
            "parent_id":      parent_id,
        }

        # ── Parent chunk ────────────────────────────────────────────────────
        parent_text = _truncate_words(section_text, PARENT_WORDS)
        if parent_text:
            docs.append({
                "id":   f"{slug}-parent-{parent_id}",
                "text": parent_text,
                "metadata": {
                    **base_meta,
                    "chunk_type": "parent",
                    "chunk_idx":  chunk_idx,
                    "parent_id":  None,   # parent chunks have no parent
                },
            })
            chunk_idx += 1

        # ── Child chunks ────────────────────────────────────────────────────
        words = section_text.split()
        if len(words) > CHILD_WORDS:
            child_chunks = _sliding_window(words, CHILD_WORDS, CHILD_OVERLAP)
        else:
            child_chunks = [section_text] if section_text else []

        for ci, child_text in enumerate(child_chunks):
            docs.append({
                "id":   f"{slug}-child-{parent_id}-{ci}",
                "text": child_text,
                "metadata": {
                    **base_meta,
                    "chunk_type": "child",
                    "chunk_idx":  chunk_idx,
                },
            })
            chunk_idx += 1

        # ── Code chunks ─────────────────────────────────────────────────────
        for ci, code_text in enumerate(code_blocks):
            docs.append({
                "id":   f"{slug}-code-{parent_id}-{ci}",
                "text": code_text,
                "metadata": {
                    **base_meta,
                    "chunk_type": "code",
                    "chunk_idx":  chunk_idx,
                },
            })
            chunk_idx += 1

    return docs


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_into_sections(soup: BeautifulSoup):
    """
    Walk the document tree and group elements under their nearest heading.
    Returns list of (heading_text, [elements]).
    """
    sections = []
    current_heading = ""
    current_elements = []

    # Flatten top-level children; headings are section delimiters
    for elem in soup.children:
        if isinstance(elem, NavigableString):
            text = str(elem).strip()
            if text:
                current_elements.append(elem)
            continue

        tag = getattr(elem, "name", None)
        if tag in ("h1", "h2", "h3", "h4"):
            if current_elements:
                sections.append((current_heading, current_elements))
            current_heading = elem.get_text(" ", strip=True)
            current_elements = []
        else:
            current_elements.append(elem)

    if current_elements:
        sections.append((current_heading, current_elements))

    # If no headings were found (flat document), treat whole doc as one section
    if not sections:
        sections = [("", list(soup.children))]

    return sections


def _sliding_window(words: List[str], size: int, overlap: int) -> List[str]:
    """Split a word list into overlapping chunks of `size` words."""
    step = max(size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunk = words[start: start + size]
        if chunk:
            chunks.append(" ".join(chunk))
        if start + size >= len(words):
            break
    return chunks


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])
