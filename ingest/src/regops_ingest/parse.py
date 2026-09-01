"""Docling-based parsing: PDF -> clause-numbered sections + structured tables.

This replaces `regdocs_mcp.build`, the provisional Day 1 parser, and writes the
same three tables `regdocs_mcp.index` defines (ADR-003). The tool surface does
not move; only the content quality does.

Why Docling rather than a better regex. The Day 1 splitter recovered clause
numbers by matching line-leading digits, which forced two heuristics that are
really structure questions in disguise: telling a footnote marker from a clause
number, and telling a page number from a section marker. Docling answers both
by *label* -- footnotes, page headers and page footers arrive tagged -- and it
hands back MAS's clause number directly in `ListItem.marker`. Measured on the
Phase 1 gate documents, the regex dropped whole clauses (3.2 -> 5, skipping "4
INTERNAL POLICIES") and found zero headings on all three.

Lettered limbs ((a), (b), (c)) arrive with `enumerated=False` and stay attached
to the clause that introduces them. That is deliberate: a limb is not citable on
its own, and splitting it off was a Day 1 bug the demo surfaced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ListItem, SectionHeaderItem, TableItem

# Structural furniture: never part of a clause's text, and never a clause start.
FURNITURE = {"page_header", "page_footer"}
# Footnotes are kept (they carry real obligations in MAS notices) but are held
# back from clause detection -- a leading "2" in a footnote is not clause 2.
FOOTNOTE = "footnote"

# A MAS clause number: 1, 1.1, 6.14.2. Anchored, because `marker` is exactly the
# enumeration Docling stripped off the front of the item.
MARKER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){0,3})\.?$")
# A top-level section header: "3 RECORD KEEPING", "3. Risk Management Practices".
HEADER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){0,3})[.)]?\s+(.{2,120})$")

FRONT_MATTER_PATH = "0"
# How much of an enclosing header to keep when it has to qualify a clause number.
MAX_SCOPE_CHARS = 40
MIN_SECTION_CHARS = 40
# Below this many extracted characters a PDF is a scan, not a document.
OCR_CHAR_THRESHOLD = 200


@dataclass
class Section:
    section_path: str
    heading: str | None
    text: str
    page_from: int
    page_to: int
    # The nearest enclosing unnumbered header ("Appendix B", "Notes to Form A1").
    # Only used to disambiguate a clause number that repeats -- see `_dedupe`.
    scope: str | None = None


@dataclass
class Table:
    section_path: str
    page: int
    caption: str | None
    rows: list[list[str]]


@dataclass
class ParsedDoc:
    sections: list[Section]
    tables: list[Table] = field(default_factory=list)
    effective_date: str | None = None
    n_pages: int = 0
    ocr_used: bool = False


def converter(*, ocr: bool = False, device: str = "cuda") -> DocumentConverter:
    """A Docling converter. OCR is off by default and routed by detection.

    Only 2 of 463 documents in this corpus are scans. Turning OCR on globally
    would pay for it on all 9,043 pages to serve 2 documents.
    """
    opts = PdfPipelineOptions()
    opts.do_ocr = ocr
    opts.do_table_structure = True
    opts.table_structure_options.do_cell_matching = True
    opts.accelerator_options = AcceleratorOptions(device=AcceleratorDevice(device), num_threads=8)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def _page_of(item) -> int:
    prov = getattr(item, "prov", None)
    return prov[0].page_no if prov else 0


def _clause_from_marker(item: ListItem) -> str | None:
    """MAS's own clause number, taken from Docling's enumeration marker."""
    if not item.enumerated or not item.marker:
        return None
    m = MARKER_RE.match(item.marker.strip())
    return m.group(1) if m else None


def _scope_label(heading: str) -> str | None:
    """A short, citable label for an enclosing header ("Notes to Form A1").

    Truncated on a word boundary and stripped of trailing punctuation, because
    this ends up inside a `section_path` that a person is expected to read.
    """
    text = " ".join(heading.split())
    if len(text) > MAX_SCOPE_CHARS:
        text = text[:MAX_SCOPE_CHARS].rsplit(" ", 1)[0]
    # "/" is the separator this label is about to be joined with.
    return text.strip(" ,.;:-").replace("/", "-") or None


def _clause_from_header(item: SectionHeaderItem) -> tuple[str | None, str]:
    """Split "3 RECORD KEEPING" into ("3", "RECORD KEEPING")."""
    text = (item.text or "").strip()
    m = HEADER_RE.match(text)
    return (m.group(1), m.group(2).strip()) if m else (None, text)


def to_sections(doc) -> tuple[list[Section], list[Table]]:
    """Walk Docling's reading order and group items under their clause number."""
    sections: list[Section] = []
    tables: list[Table] = []
    cur_path = FRONT_MATTER_PATH
    cur_heading: str | None = None
    cur_scope: str | None = None
    cur_lines: list[str] = []
    cur_from = cur_to = 0
    # The most recent top-level header, so clause 3.1 inherits "RECORD KEEPING".
    header_num: str | None = None
    header_text: str | None = None
    # The nearest unnumbered header. MAS forms notices restart clause numbering
    # inside every appendix, so "1" alone is ambiguous in a document like Notice
    # 129 -- this is what tells the second "1" apart from the first.
    scope: str | None = None

    def flush() -> None:
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(cur_lines).strip())
        if len(text) >= MIN_SECTION_CHARS:
            sections.append(Section(cur_path, cur_heading, text, cur_from, cur_to, cur_scope))

    for item, _level in doc.iterate_items():
        label = str(getattr(item, "label", "") or "").split(".")[-1].lower()
        page = _page_of(item)

        if isinstance(item, TableItem):
            rows = [[str(c) for c in row] for row in item.data.grid] if item.data else []
            caption = item.caption_text(doc) if hasattr(item, "caption_text") else None
            tables.append(Table(cur_path, page, (caption or None), [[c for c in r] for r in rows]))
            continue

        if label in FURNITURE:
            continue

        text = (getattr(item, "text", "") or "").strip()
        if not text:
            continue

        # A new clause starts here?
        new_path = None
        if isinstance(item, SectionHeaderItem):
            num, htext = _clause_from_header(item)
            if num:
                header_num, header_text = num, htext
                new_path, new_heading = num, htext
            else:
                # An unnumbered header ("Definitions", "Appendix B") titles what
                # follows, and scopes any clause numbering that restarts under it.
                header_num, header_text = None, htext
                scope = _scope_label(htext)
                cur_lines.append(text)
                cur_to = page
                continue
        elif isinstance(item, ListItem) and label != FOOTNOTE:
            num = _clause_from_marker(item)
            if num:
                new_path = num
                # "3.1" inherits the heading of header "3".
                new_heading = (
                    header_text
                    if header_num and (num == header_num or num.startswith(header_num + "."))
                    else None
                )

        if new_path is not None:
            flush()
            cur_path, cur_heading, cur_scope = new_path, new_heading, scope
            cur_lines = [text] if not isinstance(item, SectionHeaderItem) else []
            cur_from = cur_to = page
        else:
            if not cur_lines:
                cur_from = page
            cur_lines.append(text)
            cur_to = page

    flush()
    return _dedupe(sections), tables


def _dedupe(sections: list[Section]) -> list[Section]:
    """Make every `section_path` unique, disturbing citable paths as little as possible.

    A clause number repeats whenever a document restarts numbering -- appendices,
    forms, endnotes. MAS Notice 129 restarts at "1" inside roughly forty forms.
    The first occurrence keeps the bare number, which is what a compliance officer
    cites (ADR-003). A repeat is qualified by its enclosing header
    ("Notes to Form A1/1") rather than by a positional suffix, because the
    qualified form is still a citation and "1#38" is not. The ordinal suffix
    remains as a last resort so the primary key can never collide.
    """
    seen: set[str] = set()
    out: list[Section] = []
    for i, s in enumerate(sections):
        # First occurrence wins the bare number. Document order puts the main body
        # ahead of the appendices, so "Notice 129, paragraph 17" keeps citing what
        # a reader means by it, and the forms that restart at 1 are the ones that
        # carry a qualifier.
        path = s.section_path
        if path in seen and s.scope:
            path = f"{s.scope}/{s.section_path}"
        if path in seen:
            path = f"{s.section_path}#{i}"
        seen.add(path)
        out.append(Section(path, s.heading, s.text, s.page_from, s.page_to, s.scope))
    return out


def front_matter(sections: list[Section]) -> str:
    """Text before the first numbered clause -- where MAS states the date."""
    for s in sections:
        if s.section_path.startswith(FRONT_MATTER_PATH):
            return s.text
    return sections[0].text if sections else ""


def parse(
    pdf: Path, conv: DocumentConverter, *, ocr_conv: DocumentConverter | None = None
) -> ParsedDoc:
    """Parse one PDF, re-running with OCR only if it turns out to be a scan."""
    from regdocs_mcp.build import extract_effective_date

    res = conv.convert(pdf)
    doc = res.document
    sections, tables = to_sections(doc)
    ocr_used = False

    total_chars = sum(len(s.text) for s in sections)
    if total_chars < OCR_CHAR_THRESHOLD and ocr_conv is not None:
        doc = ocr_conv.convert(pdf).document
        sections, tables = to_sections(doc)
        ocr_used = True

    return ParsedDoc(
        sections=sections,
        tables=tables,
        effective_date=extract_effective_date(front_matter(sections)),
        n_pages=len(doc.pages),
        ocr_used=ocr_used,
    )
