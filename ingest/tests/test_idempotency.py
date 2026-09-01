"""Re-ingestion, and the mechanism ADR-004 says version history depends on.

ADR-004 shipped `diff_versions` with an honest empty state rather than seeding a
fake amendment, on the grounds that history is *created* by a re-fetch that
finds changed bytes under an unchanged URL (ADR-012 makes `doc_id` a hash of the
canonical URL precisely so that this works). This is the code that has to
notice, so these are the tests that make the claim real -- on synthetic bytes,
not by staging a fake amendment in the corpus.
"""

from __future__ import annotations

from regops_ingest import load
from regops_ingest.parse import Section

from .conftest import make_parsed


def _counts(conn, doc_id="aaa11111"):
    return {
        t: conn.execute(f"SELECT count(*) FROM {t} WHERE doc_id = ?", [doc_id]).fetchone()[0]
        for t in ("documents", "sections", "document_versions", "tables")
    }


class TestReingestingIsANoOp:
    def test_the_second_pass_changes_nothing(self, index_path, meta, parsed):
        conn = load.open_index(index_path)
        load.write_doc(conn, meta, parsed)
        first = _counts(conn)
        ids_first = conn.execute("SELECT section_uid FROM sections ORDER BY 1").fetchall()

        load.write_doc(conn, meta, parsed)
        assert _counts(conn) == first
        assert conn.execute("SELECT section_uid FROM sections ORDER BY 1").fetchall() == ids_first
        conn.close()

    def test_unchanged_bytes_mint_no_version(self, index_path, meta, parsed):
        conn = load.open_index(index_path)
        _, minted_first = load.write_doc(conn, meta, parsed)
        _, minted_again = load.write_doc(conn, meta, parsed)
        conn.close()
        assert minted_first is True  # the first sighting is a version
        assert minted_again is False


class TestChangedBytesCreateHistory:
    def test_a_new_sha256_adds_exactly_one_version_row(self, index_path, meta, parsed):
        conn = load.open_index(index_path)
        load.write_doc(conn, meta, parsed)

        amended = dict(meta, sha256="sha-after-the-2026-amendment")
        revised = make_parsed(
            sections=[
                Section("0", None, "NOTICE 626. Issued 28 March 2024. " + "front " * 8, 0, 0),
                Section(
                    "6.1",
                    "CUSTOMER DUE DILIGENCE",
                    "A bank shall perform enhanced customer due diligence measures when "
                    "establishing business relations with any customer.",
                    1,
                    1,
                ),
            ],
            effective="2026-07-01",
        )
        n_sections, minted = load.write_doc(conn, amended, revised)

        assert minted is True
        versions = conn.execute(
            "SELECT version_label, sha256 FROM document_versions WHERE doc_id = 'aaa11111' "
            "ORDER BY version_label"
        ).fetchall()
        assert len(versions) == 2
        assert {v[1] for v in versions} == {
            "sha-of-the-first-bytes",
            "sha-after-the-2026-amendment",
        }
        # The document now serves the revised text, not both copies of it.
        assert n_sections == 2
        assert _counts(conn)["sections"] == 2
        conn.close()

    def test_a_shrinking_reparse_leaves_no_orphan_clauses(self, index_path, meta, parsed):
        """A better parser may find *fewer* clauses; the old ones must not linger."""
        conn = load.open_index(index_path)
        load.write_doc(conn, meta, parsed)
        assert _counts(conn)["sections"] == 3

        fewer = make_parsed(
            sections=[Section("6.1", None, "A bank shall do the one remaining thing." * 2, 1, 1)]
        )
        load.write_doc(conn, dict(meta, sha256="sha-reparsed"), fewer)
        rows = conn.execute(
            "SELECT section_path FROM sections WHERE doc_id = 'aaa11111'"
        ).fetchall()
        conn.close()
        assert [r[0] for r in rows] == ["6.1"]

    def test_version_labels_do_not_collide_on_the_same_date(self, index_path, meta, parsed):
        """Two different byte-sets stated as effective the same day still both record."""
        conn = load.open_index(index_path)
        load.write_doc(conn, meta, parsed)
        load.write_doc(conn, dict(meta, sha256="sha-two"), parsed)
        labels = [
            r[0]
            for r in conn.execute(
                "SELECT version_label FROM document_versions WHERE doc_id = 'aaa11111' ORDER BY 1"
            ).fetchall()
        ]
        conn.close()
        assert labels == ["2024-03-28", "2024-03-28-2"]
