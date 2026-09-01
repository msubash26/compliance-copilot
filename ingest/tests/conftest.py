"""Fixtures for the ingest suite.

Nothing here parses a PDF. Docling needs a GPU and several seconds per
document, and the claims worth testing -- that our writer produces an index the
MCP server can serve, that re-ingestion is idempotent, that a clause number
repeating does not collide -- are all claims about our code, not about Docling.
The one place a real parse is exercised is marked `slow` and skipped without a
corpus.
"""

from __future__ import annotations

import pytest
from regops_ingest.parse import ParsedDoc, Section, Table

META = {
    "doc_id": "aaa11111",
    "issuer": "MAS",
    "doc_type": "notices",
    "title": "Notice 626 Prevention of Money Laundering",
    "url": "https://www.mas.gov.sg/x/notice-626.pdf",
    "source_page": "https://www.mas.gov.sg/regulation/notices/notice-626",
    "sha256": "sha-of-the-first-bytes",
    "fetched_at": "2026-09-03T00:00:00+00:00",
    "filename": "mas/aaa11111-notice-626.pdf",
}


def make_parsed(*, sections=None, tables=None, effective="2024-03-28") -> ParsedDoc:
    sections = (
        sections
        if sections is not None
        else [
            Section("0", None, "NOTICE 626. Issued 28 March 2024. " + "front matter " * 4, 0, 0),
            Section(
                "6.1",
                "CUSTOMER DUE DILIGENCE",
                "A bank shall perform customer due diligence measures when establishing "
                "business relations with any customer.",
                1,
                1,
            ),
            Section(
                "6.2",
                "CUSTOMER DUE DILIGENCE",
                "A bank shall not open an anonymous account or an account in a fictitious name.",
                1,
                2,
            ),
        ]
    )
    return ParsedDoc(
        sections=sections,
        tables=tables or [],
        effective_date=effective,
        n_pages=3,
    )


@pytest.fixture
def meta():
    return dict(META)


@pytest.fixture
def parsed():
    return make_parsed()


@pytest.fixture
def index_path(tmp_path):
    return tmp_path / "regdocs.duckdb"


@pytest.fixture
def table_rows():
    return [
        ["Tier", "Minimum ratio"],
        ["CET1", "6.5%"],
        ["Tier 1", "8.0%"],
    ]


@pytest.fixture
def parsed_with_table(table_rows):
    return make_parsed(tables=[Table("6.1", 2, "Table 1: Capital ratios", table_rows)])
