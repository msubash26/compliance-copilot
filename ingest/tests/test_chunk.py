"""Child chunks. The parent is the clause, so most clauses are one chunk."""

from __future__ import annotations

from regops_ingest.chunk import MAX_CHUNK_CHARS, split_section

CLAUSE = (
    "A bank shall perform customer due diligence measures when establishing business "
    "relations with any customer, and shall identify the beneficial owner. "
)


class TestShortClausesStayWhole:
    def test_a_typical_notice_clause_is_one_chunk(self):
        chunks = split_section(CLAUSE)
        assert len(chunks) == 1
        assert chunks[0].text == CLAUSE.strip()

    def test_empty_text_yields_nothing(self):
        assert split_section("   \n  ") == []


class TestLongClausesSplit:
    def _long(self):
        return split_section(CLAUSE * 40)

    def test_every_chunk_is_within_the_embedding_budget(self):
        assert all(c.char_len <= MAX_CHUNK_CHARS for c in self._long())

    def test_ordinals_are_dense_and_ordered(self):
        assert [c.ordinal for c in self._long()] == list(range(len(self._long())))

    def test_no_chunk_is_a_useless_scrap(self):
        """A trailing fragment joins the previous chunk rather than standing alone."""
        assert all(c.char_len > 100 for c in self._long())

    def test_consecutive_chunks_overlap(self):
        """An obligation spanning a seam has to stay retrievable from either side."""
        chunks = self._long()
        assert len(chunks) > 1
        tail = chunks[0].text[-60:]
        assert any(word in chunks[1].text for word in tail.split()[:3])

    def test_a_single_unbroken_sentence_is_still_bounded(self):
        chunks = split_section("word " * 2000)
        assert chunks
        assert all(c.char_len <= MAX_CHUNK_CHARS for c in chunks)

    def test_splitting_is_deterministic(self):
        assert [c.text for c in self._long()] == [c.text for c in self._long()]
