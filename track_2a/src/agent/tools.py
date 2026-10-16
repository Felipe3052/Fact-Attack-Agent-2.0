"""
LangChain @tool definitions for Fact Attack Agent 2.0 (SW5 Folie 21-24).
Exposes booklet parsing, TOC inspection, part context, and BM25 search.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# Ensure track_2a is in sys.path
_src_root = Path(__file__).resolve().parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from pdf_parser import PDFParser
from part_context import part_pages, booklet_parts, claim_part
from retriever import PassageRetriever
from text_utils import guess_language

@tool
def get_booklet_toc(booklet_path: str) -> str:
    """Schlägt das Inhaltsverzeichnis (Table of Contents) eines Schweizer Abstimmungsbüchleins nach.
    Liefert die Vorlagentitel und die Seitenzahlen der jeweiligen Sektionen.
    """
    if not os.path.exists(booklet_path):
        return f"Fehler: Booklet-Datei '{booklet_path}' nicht gefunden."
    parser = PDFParser(booklet_path)
    booklet_data = parser.parse()
    parts = booklet_parts(
        booklet_data.get("toc_lines", []),
        {p["page_number"]: p["text"] for p in booklet_data.get("pages", [])},
        len(booklet_data.get("pages", [])),
        booklet_data.get("speaker_of", {})
    )
    if not parts:
        return "Kein Inhaltsverzeichnis maschinell auflösbar."
    lines = []
    for v in parts:
        lines.append(f"Vorlage: {v.get('title')}")
        for part, pages in v.get("parts", {}).items():
            lines.append(f"  - {part}: Seiten {pages}")
    return "\n".join(lines)

@tool
def get_vote_section_context(booklet_path: str, claim: str, vote_title: Optional[str] = None) -> str:
    """Extrahiert gezielt die relevante Sektion (Part-Selection) aus dem Abstimmungsbüchlein.
    Nutzt Inhaltsverzeichnis und Claims-Eröffnung ('Laut der Zusammenfassung...', 'Das Komitee argumentiert...').
    """
    if not os.path.exists(booklet_path):
        return ""
    parser = PDFParser(booklet_path)
    booklet_data = parser.parse()
    parts = booklet_parts(
        booklet_data.get("toc_lines", []),
        {p["page_number"]: p["text"] for p in booklet_data.get("pages", [])},
        len(booklet_data.get("pages", [])),
        booklet_data.get("speaker_of", {})
    )
    found = part_pages(claim, vote_title, parts)
    if not found:
        return ""
    part, pages = found
    by_page = {p["page_number"]: p["text"] for p in booklet_data.get("pages", [])}
    selected_texts = [f"[Seite {pg}]:\n" + by_page.get(pg, "") for pg in pages if pg in by_page]
    return "\n\n".join(selected_texts)

@tool
def search_booklet_lexical(booklet_path: str, query: str, top_k: int = 5) -> str:
    """Führt eine mehrsprachige BM25-Volltextsuche über alle Seiten des Abstimmungsbüchleins durch."""
    if not os.path.exists(booklet_path):
        return ""
    parser = PDFParser(booklet_path)
    booklet_data = parser.parse()
    passages = booklet_data.get("paragraphs") or booklet_data.get("pages", [])
    if not passages:
        return ""
    retriever = PassageRetriever(passages)
    results = retriever.search(query, k=top_k)
    snippets = []
    for r in results:
        snippets.append(f"[Seite {r.page}] (Score: {r.score:.3f}):\n{r.text[:800]}...")
    return "\n\n".join(snippets)
