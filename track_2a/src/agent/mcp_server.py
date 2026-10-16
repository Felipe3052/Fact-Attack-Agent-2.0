"""
FastMCP Server for Fact Attack Agent 2.0 (SW4 Folie 12-13).
Standardizes access to Swiss Voting Booklets over the Model Context Protocol.
"""
import sys
from pathlib import Path
from typing import Optional, List
from fastmcp import FastMCP

# Ensure track_2a is in sys.path
_src_root = Path(__file__).resolve().parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from pdf_parser import PDFParser
from part_context import resolve_part_context
from retriever import PassageRetriever

mcp = FastMCP("fact-attack-swiss-booklets")

@mcp.tool()
def get_booklet_toc_mcp(booklet_path: str) -> str:
    """Ruft das Inhaltsverzeichnis eines offiziellen Schweizer Abstimmungsbüchleins ab."""
    parser = PDFParser(booklet_path)
    contents = parser.get_contents()
    if not contents:
        return "Kein Inhaltsverzeichnis verfügbar."
    return str(contents)

@mcp.tool()
def extract_vote_section_mcp(booklet_path: str, claim: str, vote_title: Optional[str] = None) -> str:
    """Extrahiert die exakte Vorlagen-Sektion für eine Behauptung (Part-Selection)."""
    parser = PDFParser(booklet_path)
    res = resolve_part_context(parser, claim, vote_title)
    if res and res.pages:
        return res.text
    return "Kein passender Sektionstext gefunden."

@mcp.tool()
def search_booklet_bm25_mcp(booklet_path: str, query: str, top_k: int = 5) -> str:
    """Mehrsprachige lexikalische BM25-Suche im Booklet."""
    parser = PDFParser(booklet_path)
    retriever = PassageRetriever(parser)
    results = retriever.search(query, k=top_k)
    return "\n\n".join([f"[Seite {r.page}]: {r.text[:600]}" for r in results])

if __name__ == "__main__":
    mcp.run()
