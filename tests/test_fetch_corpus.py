"""Offline tests for the MAS corpus fetcher. No network: CI must not crawl a statutory board."""

from __future__ import annotations

from regops_ingest.fetch_corpus import (
    USER_AGENT,
    canonical,
    extract_pdfs,
    make_doc_id,
    slugify,
)


class TestCanonical:
    def test_drops_query_and_fragment(self):
        assert (
            canonical("https://www.mas.gov.sg/a/b.pdf?v=2#page=4")
            == "https://www.mas.gov.sg/a/b.pdf"
        )

    def test_normalises_host_case_and_trailing_slash(self):
        assert canonical("https://WWW.MAS.GOV.SG/a/b/") == "https://www.mas.gov.sg/a/b"


class TestDocId:
    def test_is_stable(self):
        assert make_doc_id("https://www.mas.gov.sg/x.pdf") == make_doc_id(
            "https://www.mas.gov.sg/x.pdf"
        )

    def test_ignores_cache_busting_query(self):
        """Same document, different cache-buster, must be one logical doc (Day 3 idempotency)."""
        assert make_doc_id("https://www.mas.gov.sg/x.pdf?v=1") == make_doc_id(
            "https://www.mas.gov.sg/x.pdf?v=9"
        )

    def test_differs_by_document(self):
        assert make_doc_id("https://www.mas.gov.sg/a.pdf") != make_doc_id(
            "https://www.mas.gov.sg/b.pdf"
        )


class TestExtractPdfs:
    HTML = """
    <html><head><title>Notice 626 AML/CFT</title></head><body>
      <a href="/-/media/notice-626.pdf">current</a>
      <a href="/-/media/notice-626.pdf?v=2">same doc, cache-busted</a>
      <a href="https://www.mas.gov.sg/-/media/notice-626-amendment.pdf">amendment</a>
      <a href="/regulation/notices/notice-627">not a pdf</a>
    </body></html>
    """

    def test_reads_title(self):
        title, _ = extract_pdfs(self.HTML, "https://www.mas.gov.sg/regulation/notices/notice-626")
        assert title == "Notice 626 AML/CFT"

    def test_resolves_relative_and_dedupes_by_canonical_url(self):
        _, pdfs = extract_pdfs(self.HTML, "https://www.mas.gov.sg/regulation/notices/notice-626")
        assert pdfs == [
            "https://www.mas.gov.sg/-/media/notice-626.pdf",
            "https://www.mas.gov.sg/-/media/notice-626-amendment.pdf",
        ]

    def test_ignores_non_pdf_links(self):
        _, pdfs = extract_pdfs(self.HTML, "https://www.mas.gov.sg/x")
        assert all(p.endswith(".pdf") for p in pdfs)


def test_slugify_is_filesystem_safe():
    assert slugify("https://x/a b/c%20d.pdf") == "c-20d.pdf"


def test_user_agent_keeps_the_mozilla_prefix():
    """MAS's WAF serves an HTML 'Maintenance' page to any UA without this prefix.

    The failure is silent — HTTP 200 with no <loc> elements, which reads as an empty sitemap
    rather than a refusal. Keep the product token and contact URL so the crawler stays
    identifiable.
    """
    assert USER_AGENT.startswith("Mozilla/5.0 (compatible;")
    assert "regops-corpus" in USER_AGENT
    assert "+https://" in USER_AGENT
