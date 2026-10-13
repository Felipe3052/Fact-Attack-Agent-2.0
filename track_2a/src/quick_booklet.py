"""
A booklet read page by page, for the first cases of a booklet that is not parsed yet (QUICK_PARTS).

A new booklet takes seconds to parse in full (pypdf and PyMuPDF, every page), and no request is in flight while the
first one is parsed (that time is scored). With part selection (PART_CONTEXT) a case needs only the contents page,
the headings of its vote's parts and the pages of its part, so its request can go out after a few pages. The full
parse runs on in the background (src/page_pool.py, prefetch thread) and serves every later case.

Every page is read with the functions the full parse uses (`extract_page_text` for the model's text, `source_page`
for the contents and the evidence) and turned into the same passage, so a case gets byte-identical model input and
evidence on either path (checked on all task A cases of the dataset and the holdout, see
docs/independent_experiments.md). Readers are not thread-safe: one lock per booklet.
"""

import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, List, Optional

_SPEAKERS = {"Arguments of the initiative/referendum committee": "committee",
             "Arguments of the Federal Council and Parliament": "federal_council"}


class QuickBooklet:
    def __init__(self, pdf_path):
        self.path = str(Path(pdf_path).resolve())
        self._lock = threading.Lock()
        self._pypdf = None
        self._mupdf = None
        self._bytes: Optional[bytes] = None  # read once: no file stays open (and a read-only /data is enough)
        self._text: Dict[int, str] = {}
        self._source: Dict[int, Optional[Dict[str, Any]]] = {}
        self._mu_text: Dict[int, str] = {}
        self.parts_cache: Dict[str, Any] = {}

    # -- page access (same calls as the full parse) -----------------------------------------------------------------
    def n_pages(self) -> int:
        with self._lock:
            return len(self._reader().pages)

    def _data(self) -> bytes:
        if self._bytes is None:
            self._bytes = Path(self.path).read_bytes()
        return self._bytes

    def _reader(self):
        if self._pypdf is None:
            import io
            import pypdf
            self._pypdf = pypdf.PdfReader(io.BytesIO(self._data()))
        return self._pypdf

    def text(self, n: int) -> str:
        """pypdf text of page n (1-based), as PDFParser.extract_pages returns it ('' for an empty page)."""
        with self._lock:
            if n not in self._text:
                from src.pdf_parser import extract_page_text
                reader = self._reader()
                self._text[n] = (extract_page_text(reader, n - 1, self.path) or "") if 1 <= n <= len(reader.pages) else ""
            return self._text[n]

    def _doc(self):
        if self._mupdf is None:
            import pymupdf
            self._mupdf = pymupdf.open(stream=self._data(), filetype="pdf")
        return self._mupdf

    def mupdf_pages(self) -> int:
        with self._lock:
            return len(self._doc())

    def mupdf_text(self, n: int) -> str:
        """PyMuPDF text of page n as source_page reads it (text only, no blocks: fast; for the contents and headings)."""
        with self._lock:
            if n not in self._mu_text:
                doc = self._doc()
                self._mu_text[n] = doc[n - 1].get_text(sort=True) if 1 <= n <= len(doc) else ""
            return self._mu_text[n]

    def source(self, n: int) -> Optional[Dict[str, Any]]:
        """PyMuPDF page n as the parse stores it for the evidence (None for a page the full parse leaves out)."""
        if not self.text(n):  # the full parse keeps source pages only for pages with pypdf text
            return None
        with self._lock:
            if n not in self._source:
                from src.evidence import source_page
                doc = self._doc()
                self._source[n] = source_page(doc[n - 1]) if 1 <= n <= len(doc) else None
            return self._source[n]

    # -- what the full parse derives from the pages -----------------------------------------------------------------
    def passage(self, n: int) -> Optional[Dict[str, Any]]:
        """The page-level passage of page n, as extract_paragraphs builds it (first chunk of at least 40 characters)."""
        text = self.text(n)
        for chunk in text.split("\n\n"):
            clean = " ".join(chunk.split()).strip()
            if len(clean) >= 40:
                return {"page_number": n, "text": clean}
        return None

    def first_texts(self, k: int = 3) -> List[str]:
        """pypdf text of the first k pages that have text (the full parse's pages[:k])."""
        out, n, total = [], 1, self.n_pages()
        while len(out) < k and n <= total:
            if self.text(n):
                out.append(self.text(n))
            n += 1
        return out

    def speakers(self, pages: List[int]) -> Dict[int, Optional[str]]:
        """Speaker labels of an arguments range, by the parser's heading and closing-box rules applied to its pages."""
        from src.pdf_parser import TOC_SECTION, detect_closing_speaker, detect_section_heading
        texts = [self.text(n) for n in pages]
        headings = [detect_section_heading(t) for t in texts]
        sections, current = [], None
        for heading in headings:
            if heading == TOC_SECTION:
                current = None
            elif heading:
                current = heading
            sections.append(current)
        for i, t in enumerate(texts):
            speaker = detect_closing_speaker(t)
            if not speaker:
                continue
            for j in (i, i - 1):
                if j >= 0 and not headings[j] and pages[i] - pages[j] <= 1:
                    sections[j] = speaker
            k = i + 1
            while k < len(pages) and not headings[k] and sections[k] in _SPEAKERS:
                sections[k] = None
                k += 1
        return {n: _SPEAKERS.get(s) for n, s in zip(pages, sections)}


class SourceTexts(Mapping):
    """
    {page: PyMuPDF text}, read on access, for part_context.booklet_parts. The full parse keys these by the pages with
    pypdf text; here a page counts if PyMuPDF finds text on it, so the contents check reads no page with pypdf (the
    equality check over all dataset and holdout cases shows the same parts).
    """

    def __init__(self, booklet: QuickBooklet):
        self.b = booklet
        self._n = booklet.mupdf_pages()

    def _has(self, n):
        return isinstance(n, int) and 1 <= n <= self._n and bool(self.b.mupdf_text(n).strip())

    def __getitem__(self, n):
        if not self._has(n):
            raise KeyError(n)
        return self.b.mupdf_text(n)

    def get(self, n, default=None):
        try:
            return self[n]
        except KeyError:
            return default

    def last_page(self):
        """The last page the full parse stores (the highest page with pypdf text)."""
        n = self._n
        while n > 0 and not self._has(n):
            n -= 1
        return n

    def __iter__(self):
        # keys in order; a page is a key if the full parse would store it (pypdf text present)
        return (n for n in range(1, self._n + 1) if self._has(n))

    def __len__(self):
        return sum(1 for _ in self)

    def __contains__(self, n):
        return self._has(n)


class QuickSourcePages:
    """Evidence source pages read on demand (the interface of evidence.ParsedSourcePages)."""

    def __init__(self, booklet: QuickBooklet):
        self.b = booklet

    def get(self, case, page):
        if type(page) is not int or page < 1:
            return None
        return self.b.source(page)


_BOOKLETS: Dict[str, QuickBooklet] = {}
_GUARD = threading.Lock()


def booklet(pdf_path) -> QuickBooklet:
    key = str(Path(pdf_path).resolve())
    with _GUARD:
        if key not in _BOOKLETS:
            _BOOKLETS[key] = QuickBooklet(key)
        return _BOOKLETS[key]
