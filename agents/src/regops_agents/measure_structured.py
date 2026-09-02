"""Measure the three validation layers over the golden sample.

Same 30 questions as `toolcall_probe`, so the two Day 6 measurements describe
the same set and can be read next to each other. Context comes from the *BM25*
arm by default -- not because it is the best retriever (Day 5 says it is the
worst) but because it is what `search_notices` does, and this measures what an
agent on the portable tool surface actually has to work with.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from regops_retrieval.context import assemble_context
from regops_retrieval.index import Index

from regops_agents.structured import MODEL, answer_once, rates, write
from regops_agents.toolcall_probe import load_sample

TOP_K = 5


def _arm(name: str, ix: Index):
    """The retrieval behind the answer, as one of the agent's two tool surfaces.

    `bm25` is exactly what `search_notices` does -- the portable MCP surface, and
    Day 5's bottom rung. `c4` is what `search_local` does. Running the identical
    question set, prompt and validator over both is how the tool-surface choice
    becomes a number rather than an architectural preference (ADR-025).
    """
    from regops_retrieval.retrievers import Bm25

    if name == "bm25":
        return Bm25(ix)

    from regops_retrieval.configs import build
    from regops_retrieval.rerank import CrossEncoder
    from regops_retrieval.retrievers import QuestionVectors

    from regops_agents.tools import BEST

    return build(BEST, ix, QuestionVectors(BEST.embed_model), scorer=CrossEncoder())


def _find_vectors(retriever):
    """The `QuestionVectors` inside a composed retriever, wherever it ended up.

    `build()` nests arms inside RRF inside Rerank, so the embedder is not a
    top-level attribute. Walking for it beats threading it through three
    constructors that have no other reason to know about pre-warming.
    """
    from regops_retrieval.retrievers import QuestionVectors

    seen, stack = set(), [retriever]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, QuestionVectors):
            return obj
        for v in vars(obj).values() if hasattr(obj, "__dict__") else []:
            if isinstance(v, (list, tuple)):
                stack.extend(v)
            elif hasattr(v, "__dict__") or isinstance(v, QuestionVectors):
                stack.append(v)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--repair", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--arm", choices=("bm25", "c4"), default="bm25")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    items = load_sample(a.golden)
    out_path = a.out or Path(f"results/day6/structured_{a.arm}.json")
    ix = Index(a.index)
    arm = _arm(a.arm, ix)

    # Batch by model, for the fourth day running. The C4 arm embeds each question
    # with `nomic-embed-text` and then answers it with `qwen3.5:9b`; interleaved,
    # that is one model swap per item. Every question vector is computed first,
    # then nothing but the generator is touched.
    if a.arm != "bm25":
        vecs = getattr(arm, "vectors", None) or _find_vectors(arm)
        if vecs is not None:
            t0 = time.perf_counter()
            for it in items:
                vecs.get(it["question"])
            print(f"pre-embedded {len(items)} questions in {time.perf_counter() - t0:.1f}s")

    rows = []
    try:
        for i, it in enumerate(items, 1):
            ctx = assemble_context(ix, arm.search(it["question"], 20), top_k=TOP_K)
            v = answer_once(
                ix,
                it["question"],
                ctx.text,
                model=a.model,
                repair=a.repair,
                item_id=it["id"],
            )
            rows.append(v)
            mark = "ok " if v.valid else "BAD"
            if v.repaired:
                note = "  repaired"
            else:
                note = "  " + v.violations[0][:70] if v.violations else ""
            print(f"  [{i:>2}/{len(items)}] {it['id']}  {mark}{note}")
    finally:
        ix.close()

    write(rows, out_path)
    s = rates(rows)
    print(
        f"\nunaided   shape {s['shape_ok_first']}/{s['n']}   "
        f"references {s['reference_ok_first']}/{s['n']}"
    )
    print(f"repaired  shape {s['shape_ok']}/{s['n']}   references {s['reference_ok']}/{s['n']}")
    print(
        f"repair    attempted {s['repair_attempted']}, fixed {s['repaired']}"
        + (f" ({s['repair_rate']:.0%})" if s["repair_rate"] is not None else "")
    )
    print(f"abstained {s['abstained']}/{s['n']}  ·  p50 {s['p50_s']}s\n-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
