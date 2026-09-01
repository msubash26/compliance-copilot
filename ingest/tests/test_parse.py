"""The parsing decisions that are ours rather than Docling's.

Docling's own layout model is not under test here -- that was settled by the
Phase 1 gate, by reading its output on three real documents. What is under test
is what we do with it: which labels start a clause, how a repeated clause number
is disambiguated, and when a PDF is treated as a scan.
"""

from __future__ import annotations

from dataclasses import dataclass

from regops_ingest import parse as P
from regops_ingest.parse import Section


@dataclass
class FakeMarker:
    """Enough of docling's ListItem for `_clause_from_marker`."""

    marker: str
    enumerated: bool = True


class TestClauseNumbers:
    def test_a_marker_is_mas_own_clause_number(self):
        assert P._clause_from_marker(FakeMarker("6.14")) == "6.14"
        assert P._clause_from_marker(FakeMarker("1.")) == "1"
        assert P._clause_from_marker(FakeMarker("6.14.2")) == "6.14.2"

    def test_a_lettered_limb_is_not_a_clause(self):
        """(a)/(b) belong to the clause that introduces them, not beside it."""
        assert P._clause_from_marker(FakeMarker("(a)", enumerated=False)) is None
        assert P._clause_from_marker(FakeMarker("", enumerated=False)) is None

    def test_a_bullet_is_not_a_clause(self):
        assert P._clause_from_marker(FakeMarker("-")) is None


class TestScopeLabels:
    def test_it_trims_to_a_word_boundary(self):
        label = P._scope_label("Instructions for completion of Form A1, Notes and Annexes A1-1")
        assert label == "Instructions for completion of Form A1"
        assert not label.endswith(",")

    def test_it_never_contains_the_join_separator(self):
        assert "/" not in P._scope_label("Notes to Form A1 / A2")

    def test_a_short_heading_survives_intact(self):
        assert P._scope_label("Appendix B") == "Appendix B"


class TestDisambiguatingRepeatedClauseNumbers:
    """MAS Notice 129 restarts numbering at 1 inside roughly forty forms."""

    def _sections(self):
        return [
            Section("1", None, "main body clause one", 1, 1, scope="Introduction"),
            Section("2", None, "main body clause two", 1, 1, scope="Introduction"),
            Section("1", None, "appendix note one", 36, 36, scope="Notes to Form A1"),
            Section("2", None, "appendix note two", 36, 36, scope="Notes to Form A1"),
        ]

    def test_the_main_body_keeps_the_bare_citable_number(self):
        out = P._dedupe(self._sections())
        assert [s.section_path for s in out[:2]] == ["1", "2"]

    def test_a_repeat_is_qualified_by_its_enclosing_header(self):
        out = P._dedupe(self._sections())
        assert [s.section_path for s in out[2:]] == [
            "Notes to Form A1/1",
            "Notes to Form A1/2",
        ]

    def test_every_path_is_unique_even_with_no_scope_to_use(self):
        sections = [Section("1", None, f"text {i}", 1, 1, scope=None) for i in range(3)]
        paths = [s.section_path for s in P._dedupe(sections)]
        assert len(set(paths)) == 3

    def test_paths_stay_stable_across_two_identical_parses(self):
        first = [s.section_path for s in P._dedupe(self._sections())]
        second = [s.section_path for s in P._dedupe(self._sections())]
        assert first == second


class TestOcrIsRoutedByDetection:
    """Two documents of 463 are scans. Global OCR would bill 9,043 pages for them."""

    class _Doc:
        pages = {1: object()}

    class _Conv:
        def __init__(self, chars):
            self.chars, self.calls = chars, 0

        def convert(self, pdf):
            self.calls += 1
            doc = TestOcrIsRoutedByDetection._Doc()
            return type("Res", (), {"document": doc})()

    def _patch(self, monkeypatch, chars):
        monkeypatch.setattr(
            P, "to_sections", lambda doc: ([Section("1", None, "x" * chars, 0, 0)], [])
        )

    def test_a_text_pdf_never_touches_the_ocr_converter(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, P.OCR_CHAR_THRESHOLD + 1)
        plain, ocr = self._Conv(0), self._Conv(0)
        out = P.parse(tmp_path / "x.pdf", plain, ocr_conv=ocr)
        assert (plain.calls, ocr.calls) == (1, 0)
        assert out.ocr_used is False

    def test_a_scan_is_re_run_through_ocr(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, P.OCR_CHAR_THRESHOLD - 1)
        plain, ocr = self._Conv(0), self._Conv(0)
        out = P.parse(tmp_path / "x.pdf", plain, ocr_conv=ocr)
        assert (plain.calls, ocr.calls) == (1, 1)
        assert out.ocr_used is True

    def test_without_an_ocr_converter_a_scan_is_reported_not_retried(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, P.OCR_CHAR_THRESHOLD - 1)
        plain = self._Conv(0)
        out = P.parse(tmp_path / "x.pdf", plain, ocr_conv=None)
        assert plain.calls == 1
        assert out.ocr_used is False
