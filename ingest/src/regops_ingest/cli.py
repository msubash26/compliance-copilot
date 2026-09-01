"""`regops-ingest` -- build the index, and trace one clause end to end."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

from regops_ingest import load
from regops_ingest import parse as parse_mod


def _manifest(corpus: Path) -> list[dict]:
    path = corpus / "manifest.jsonl"
    if not path.exists():
        sys.exit(f"error: no manifest at {path}")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _stratified(rows: list[dict], pages: dict[str, int], n: int, seed: int = 0) -> list[dict]:
    """Sample across page-count buckets, so the timing is not all short notices.

    The corpus holds 26% of its pages in 1.5% of its files. A uniform sample of
    20 documents would almost certainly miss every one of them and produce a
    seconds-per-page figure that is wrong in the expensive direction.
    """
    buckets: dict[str, list[dict]] = {"s": [], "m": [], "l": [], "xl": []}
    for r in rows:
        p = pages.get(r["doc_id"], 0)
        key = "s" if p <= 10 else "m" if p <= 50 else "l" if p <= 100 else "xl"
        buckets[key].append(r)
    rng = random.Random(seed)
    out: list[dict] = []
    per = max(1, n // len(buckets))
    for key in ("s", "m", "l", "xl"):
        pool = buckets[key]
        rng.shuffle(pool)
        out.extend(pool[:per])
    return out[:n]


def cmd_build(a: argparse.Namespace) -> int:
    rows = _manifest(a.corpus)
    if a.doc_type:
        rows = [r for r in rows if r["doc_type"] == a.doc_type]
    if a.only:
        wanted = set(a.only.split(","))
        rows = [r for r in rows if r["doc_id"] in wanted]

    conn = load.open_index(a.out)

    if a.sample:
        pages = {
            r[0]: r[1] for r in conn.execute("SELECT doc_id, n_sections FROM documents").fetchall()
        }
        # No page counts on a cold index: fall back to file size as the proxy.
        if not pages:
            pages = {r["doc_id"]: max(1, r.get("bytes", 0) // 40_000) for r in rows}
        rows = _stratified(rows, pages, a.sample)

    if a.resume:
        done = {
            r[0]
            for r in conn.execute(
                "SELECT d.doc_id FROM documents d WHERE d.n_sections > 0"
            ).fetchall()
        }
        before = len(rows)
        rows = [r for r in rows if r["doc_id"] not in done]
        print(f"resuming: {before - len(rows)} already indexed, {len(rows)} to go", flush=True)

    conv = parse_mod.converter(device=a.device)
    ocr_conv = None if a.no_ocr else parse_mod.converter(ocr=True, device=a.device)

    per_doc, timings, failures, ocr_docs, versioned = [], [], [], [], []
    t_start = time.perf_counter()
    for n, r in enumerate(rows, 1):
        pdf = a.corpus / r["filename"]
        if not pdf.exists():
            failures.append((r["doc_id"], "missing file"))
            continue
        t0 = time.perf_counter()
        try:
            parsed = parse_mod.parse(pdf, conv, ocr_conv=ocr_conv)
        except Exception as exc:  # noqa: BLE001 - one bad PDF must not stop the build
            failures.append((r["doc_id"], str(exc)[:90]))
            continue
        dt = time.perf_counter() - t0
        n_sec, minted = load.write_doc(conn, r, parsed)
        per_doc.append(n_sec)
        timings.append((r["doc_id"], parsed.n_pages, dt))
        if parsed.ocr_used:
            ocr_docs.append(r["doc_id"])
        if minted:
            versioned.append(r["doc_id"])
        print(
            f"  [{n}/{len(rows)}] {r['doc_id']} {parsed.n_pages:>4}p "
            f"{n_sec:>4} sections {len(parsed.tables):>3} tables {dt:6.1f}s"
            f"{' OCR' if parsed.ocr_used else ''}",
            flush=True,
        )

    print("building FTS index...", flush=True)
    load.build_fts(conn)
    conn.close()

    wall = time.perf_counter() - t_start
    total_pages = sum(t[1] for t in timings)
    print(f"\nindexed {len(per_doc)} documents, {sum(per_doc)} sections -> {a.out}")
    print(f"{total_pages} pages in {wall:.0f}s")
    if total_pages:
        print(f"  {wall / total_pages:.3f} s/page overall")
        per_page = sorted(dt / p for _, p, dt in timings if p)
        print(
            f"  per-document s/page: median {statistics.median(per_page):.3f}, "
            f"min {per_page[0]:.3f}, max {per_page[-1]:.3f}"
        )
    if per_doc:
        print(
            f"sections per document: median {statistics.median(per_doc)}, "
            f"min {min(per_doc)}, max {max(per_doc)}"
        )
    if ocr_docs:
        print(f"OCR used on {len(ocr_docs)}: {ocr_docs}")
    if versioned:
        print(f"new version rows: {len(versioned)}")
    if failures:
        print(f"{len(failures)} failed: {failures[:5]}")
    return 1 if per_doc and statistics.median(per_doc) <= 1 else 0


def cmd_trace(a: argparse.Namespace) -> int:
    """PDF -> clause -> chunk -> context -> embedding, for one clause."""
    conn = load.open_index(a.index)
    uid = f"{a.doc_id}:{a.section_path}"
    doc = conn.execute(
        "SELECT doc_id, title, issuer, doc_type, url, sha256, effective_date, n_sections "
        "FROM documents WHERE doc_id = ?",
        [a.doc_id],
    ).fetchone()
    if not doc:
        sys.exit(f"no document {a.doc_id} in {a.index}")
    sec = conn.execute(
        "SELECT section_path, heading, ordinal, text, char_len, page_from, page_to "
        "FROM sections WHERE section_uid = ?",
        [uid],
    ).fetchone()
    if not sec:
        near = conn.execute(
            "SELECT section_path FROM sections WHERE doc_id = ? ORDER BY ordinal LIMIT 12",
            [a.doc_id],
        ).fetchall()
        sys.exit(f"no section {a.section_path!r}. First paths: {[r[0] for r in near]}")

    print(f"DOCUMENT  {doc[0]}  {doc[1]}")
    print(f"          {doc[2]} / {doc[3]} · effective {doc[6]} · {doc[7]} sections")
    print(f"          {doc[4]}")
    print(f"          sha256 {doc[5]}")
    vers = conn.execute(
        "SELECT version_label, sha256, filename FROM document_versions WHERE doc_id = ? "
        "ORDER BY version_label",
        [a.doc_id],
    ).fetchall()
    print(f"VERSIONS  {[(v[0], (v[1] or '')[:8]) for v in vers]}")
    print(f"SOURCE    {vers[0][2] if vers else '?'}  pages {sec[5]}-{sec[6]}")
    print(f"\nSECTION   [{sec[0]}] {sec[1] or ''}  (ordinal {sec[2]}, {sec[4]} chars)")
    print("-" * 78)
    print(sec[3][: a.max_chars])
    if len(sec[3]) > a.max_chars:
        print(f"... [{len(sec[3]) - a.max_chars} more chars]")
    print("-" * 78)

    chunks = conn.execute(
        "SELECT chunk_id, ordinal, char_len, token_len, text, context_text "
        "FROM chunks WHERE section_uid = ? ORDER BY ordinal",
        [uid],
    ).fetchall()
    print(f"\nCHUNKS    {len(chunks)}")
    for c in chunks:
        print(f"  [{c[1]}] {c[0]}  {c[2]} chars / {c[3]} tokens")
        if c[5]:
            print(f"       context: {c[5]}")
        print(f"       text:    {c[4][:160]!r}")
        embs = conn.execute(
            "SELECT model, dim, sqrt(list_dot_product(vec, vec)) FROM embeddings "
            "WHERE chunk_id = ? ORDER BY model",
            [c[0]],
        ).fetchall()
        for e in embs:
            print(f"       embed:   {e[0]} dim={e[1]} norm={e[2]:.4f}")
        if not embs:
            print("       embed:   (none)")

    tabs = conn.execute(
        "SELECT table_id, page, n_rows, n_cols, caption FROM tables WHERE section_uid = ?",
        [uid],
    ).fetchall()
    if tabs:
        print(f"\nTABLES    {len(tabs)}")
        for t in tabs:
            print(f"  {t[0]}  p{t[1]}  {t[2]}x{t[3]}  {t[4] or ''}")
    conn.close()
    return 0


def cmd_chunk(a: argparse.Namespace) -> int:
    """Sections -> child chunks. Cheap and re-runnable; parsing is the expensive half."""
    from regops_ingest.chunk import split_section

    conn = load.open_index(a.index)
    rows = conn.execute(
        "SELECT section_uid, doc_id, text FROM sections ORDER BY doc_id, ordinal"
    ).fetchall()
    conn.execute("DELETE FROM chunks")
    n_chunks = 0
    sizes = []
    for section_uid, doc_id, text in rows:
        for c in split_section(text):
            conn.execute(
                "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?)",
                [
                    f"{section_uid}#{c.ordinal}",
                    doc_id,
                    section_uid,
                    c.ordinal,
                    c.text,
                    None,
                    c.char_len,
                    None,
                ],
            )
            n_chunks += 1
            sizes.append(c.char_len)
    conn.close()
    print(f"{len(rows)} sections -> {n_chunks} chunks")
    if sizes:
        sizes.sort()
        print(
            f"chars/chunk: median {statistics.median(sizes):.0f}, "
            f"p95 {sizes[int(len(sizes) * 0.95)]}, max {sizes[-1]}"
        )
        print(f"chunks/section: {n_chunks / max(len(rows), 1):.2f}")
    return 0


def cmd_context(a: argparse.Namespace) -> int:
    """Write a one-sentence locator for every chunk (ADR-015)."""
    import asyncio

    from regops_ingest.context import Outline, contextualise, spine_for

    conn = load.open_index(a.index)
    where = "WHERE c.doc_id = ?" if a.doc_id else ""
    params = [a.doc_id] if a.doc_id else []
    if not a.redo:
        where += (" AND" if where else "WHERE") + " c.context_text IS NULL"
    # One locator per *clause*, not per chunk. The parent in this corpus is a real
    # unit (ADR-014), so the sentence that situates chunk 2 of clause 6.14 is the
    # sentence that situates clause 6.14 -- generating it twice buys nothing and
    # costs, measured here, 3.9 hours against 2.0 over 22,090 chunks. The excerpt
    # sent to the model is the clause's first chunk, which is what the locator is
    # about. See ADR-015.
    rows = conn.execute(
        f"""SELECT c.section_uid, arg_min(c.text, c.ordinal), any_value(s.section_path),
                   any_value(s.heading), any_value(d.doc_id), any_value(d.title),
                   any_value(d.doc_type), any_value(d.issuer), any_value(d.effective_date)
            FROM chunks c
            JOIN sections s ON s.section_uid = c.section_uid
            JOIN documents d ON d.doc_id = c.doc_id
            {where}
            GROUP BY c.section_uid
            ORDER BY c.section_uid
            {"LIMIT " + str(a.limit) if a.limit else ""}""",
        params,
    ).fetchall()
    if not rows:
        print("nothing to contextualise")
        return 0

    # One clause spine per document, reused by every clause in it.
    spines: dict[str, list[tuple[str, str | None]]] = {}
    for doc_id in {r[4] for r in rows}:
        spines[doc_id] = conn.execute(
            "SELECT section_path, heading FROM sections WHERE doc_id = ? ORDER BY ordinal",
            [doc_id],
        ).fetchall()

    items = []
    for section_uid, text, section_path, heading, doc_id, title, doc_type, issuer, eff in rows:
        outline = Outline(
            title=title,
            doc_type=doc_type,
            issuer=issuer,
            effective_date=str(eff) if eff else None,
            section_path=section_path,
            heading=heading,
            spine=spine_for(spines[doc_id], section_path),
        )
        items.append((section_uid, outline, text))

    print(f"contextualising {len(items)} clauses, concurrency {a.concurrency}", flush=True)
    done = {"n": 0, "fail": 0, "ptok": 0, "ctok": 0}
    t0 = time.perf_counter()

    def progress(section_uid, ctx, usage):
        done["n"] += 1
        if ctx is None:
            done["fail"] += 1
        done["ptok"] += usage.get("prompt_tokens") or 0
        done["ctok"] += usage.get("completion_tokens") or 0
        if done["n"] % 200 == 0:
            el = time.perf_counter() - t0
            print(
                f"  {done['n']}/{len(items)}  {el / done['n']:.2f}s/clause  {done['fail']} failed",
                flush=True,
            )

    out = asyncio.run(
        contextualise(
            items,
            model=a.model,
            concurrency=a.concurrency,
            on_done=progress,
            trace_sample=a.trace_sample,
        )
    )
    wall = time.perf_counter() - t0
    n_chunks = 0
    for section_uid, ctx in out.items():
        if ctx is not None:
            n_chunks += conn.execute(
                "UPDATE chunks SET context_text = ? WHERE section_uid = ?", [ctx, section_uid]
            ).fetchone()[0]
    conn.close()
    ok = sum(1 for v in out.values() if v)
    print(f"\ncontextualised {ok}/{len(items)} clauses in {wall:.0f}s ({wall / len(items):.2f}s)")
    print(f"applied to {n_chunks} chunks")
    print(f"tokens: prompt {done['ptok']}, completion {done['ctok']}")
    return 0


def cmd_embed(a: argparse.Namespace) -> int:
    """Embed every chunk twice -- raw, and with its context sentence prepended."""
    from regops_ingest import embed as emb

    conn = load.open_index(a.index)
    emb.ensure_vss(conn)
    rows = conn.execute(
        "SELECT chunk_id, text, context_text FROM chunks ORDER BY doc_id, ordinal"
    ).fetchall()
    if not rows:
        sys.exit("no chunks; run `regops-ingest chunk` first")

    arms = [(a.model, False)]
    if not a.no_context and any(r[2] for r in rows):
        arms.append((a.model + emb.CTX_SUFFIX, True))

    for label, with_ctx in arms:
        todo = [r for r in rows if (r[2] if with_ctx else True)]
        print(f"embedding {len(todo)} chunks as {label!r}", flush=True)
        conn.execute("DELETE FROM embeddings WHERE model = ?", [label])
        t0 = time.perf_counter()
        n = 0
        for i in range(0, len(todo), emb.BATCH):
            batch = todo[i : i + emb.BATCH]
            texts = [(f"{r[2]}\n\n{r[1]}" if with_ctx else r[1]) for r in batch]
            vecs, _ptok = emb.embed_batch(texts, model=a.model)
            for r, v in zip(batch, vecs, strict=True):
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?)",
                    [r[0], label, len(v), v],
                )
                if not with_ctx:
                    conn.execute(
                        "UPDATE chunks SET token_len = ? WHERE chunk_id = ? AND token_len IS NULL",
                        [max(1, len(r[1]) // 4), r[0]],
                    )
            n += len(batch)
            if n % (emb.BATCH * 10) == 0:
                el = time.perf_counter() - t0
                print(f"  {n}/{len(todo)}  {n / el:.1f} chunks/s", flush=True)
        el = time.perf_counter() - t0
        print(f"  {label}: {n} vectors in {el:.0f}s ({n / max(el, 1e-9):.1f} chunks/s)")

    print("building HNSW index...", flush=True)
    t0 = time.perf_counter()
    emb.build_hnsw(conn)
    print(f"HNSW built in {time.perf_counter() - t0:.1f}s")
    conn.close()
    size = a.index.stat().st_size / 1e6
    print(f"index file: {size:.1f} MB")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="regops-ingest", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="parse a corpus into a regdocs index")
    b.add_argument("--corpus", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--sample", type=int, default=None, help="stratified sample of N documents")
    b.add_argument("--only", default=None, help="comma-separated doc_ids")
    b.add_argument("--doc-type", default=None)
    b.add_argument("--device", default="cuda", choices=["cuda", "cpu", "auto"])
    b.add_argument("--no-ocr", action="store_true", help="never re-run scans through OCR")
    b.add_argument("--resume", action="store_true", help="skip documents already indexed")
    b.set_defaults(fn=cmd_build)

    t = sub.add_parser("trace", help="show one clause from PDF to embedding")
    t.add_argument("doc_id")
    t.add_argument("section_path")
    t.add_argument("--index", type=Path, required=True)
    t.add_argument("--max-chars", type=int, default=1200)
    t.set_defaults(fn=cmd_trace)

    c = sub.add_parser("chunk", help="split sections into child chunks")
    c.add_argument("--index", type=Path, required=True)
    c.set_defaults(fn=cmd_chunk)

    x = sub.add_parser("context", help="write a locator sentence per chunk")
    x.add_argument("--index", type=Path, required=True)
    x.add_argument("--model", default="qwen3.5:9b")
    x.add_argument("--concurrency", type=int, default=4)
    x.add_argument("--limit", type=int, default=None)
    x.add_argument("--doc-id", default=None)
    x.add_argument("--redo", action="store_true", help="overwrite existing context sentences")
    x.add_argument(
        "--trace-sample",
        type=float,
        default=0.01,
        help="fraction of calls traced to LangFuse; failures are always traced",
    )
    x.set_defaults(fn=cmd_context)

    e = sub.add_parser("embed", help="embed chunks and build the HNSW index")
    e.add_argument("--index", type=Path, required=True)
    e.add_argument("--model", default="nomic-embed-text:latest")
    e.add_argument("--no-context", action="store_true", help="skip the context-prepended arm")
    e.set_defaults(fn=cmd_embed)

    a = ap.parse_args()
    sys.exit(a.fn(a))
