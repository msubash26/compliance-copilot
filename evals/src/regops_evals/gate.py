"""The saturation gate: does this set have room to measure anything?

Day 4's founding measurement was that a naively generated golden set is
saturated -- BM25 at 92% recall@5 over probe questions, at ceiling before any
retrieval variant is applied. A sweep over seven configurations against a set
like that produces seven identical rows, and Day 5's whole deliverable
(*different architectures win on different query types*) becomes unreachable.

So the finished set gets measured, per query type, and the number is published
here rather than discovered on Day 5. Two rules govern what happens next:

- **The gate reports; it never filters.** If the aggregate is high, the remedy
  is to *add* harder categories, never to delete the items a baseline answered.
  Deleting them would tune the benchmark to embarrass a particular retriever,
  which is a worse artifact than a saturated one because the bias is hidden.
- **This runs the same two retrievers Day 5 starts from**, defined once in
  `corpus.Index`, so the baseline row here and Day 5's baseline row are
  comparable by construction rather than by coincidence.

Two metrics, because multi-span items need both. `hit@k` is the usual
any-gold-span-retrieved. `full@k` requires *every* gold span in the top k, which
is the honest bar for a `multi_hop` question: retrieving one half of a hop does
not answer it.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from regops_evals.corpus import Index, embed_one
from regops_evals.schema import read_jsonl

# Above this, the set lacks headroom and Day 5 cannot distinguish configurations.
SATURATION_CEILING = 0.80


def _recall(retrieved: list[str], gold: set[str], k: int) -> tuple[float, float]:
    top = set(retrieved[:k])
    hits = gold & top
    return (1.0 if hits else 0.0), (1.0 if gold <= top else 0.0)


def run_gate(golden: Path, index: Path, *, k: int = 5, out: Path | None = None) -> int:
    items = read_jsonl(golden)
    ix = Index(index)
    grounded = [i for i in items if i.gold_spans]
    negatives = [i for i in items if not i.gold_spans]

    rows: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Batch the embeddings first: Ollama serialises, and interleaving embed calls
    # with nothing else is still cheaper done in one pass.
    vecs = {i.id: embed_one(i.question) for i in grounded}

    for it in grounded:
        gold = {sp.section_uid for sp in it.gold_spans}
        bm = [u for u, _ in ix.search_bm25(it.question, 20)]
        dn = [u for u, _ in ix.search_dense(it.question, 20, vec=vecs[it.id])]
        for arm, got in (("bm25", bm), ("dense", dn)):
            for kk in (1, k, 20):
                hit, full = _recall(got, gold, kk)
                rows[it.query_type][f"{arm}_hit@{kk}"].append(hit)
                rows[it.query_type][f"{arm}_full@{kk}"].append(full)

    def agg(d: dict[str, list[float]]) -> dict[str, float]:
        return {m: round(statistics.mean(v), 3) for m, v in sorted(d.items())}

    per_type = {qt: agg(d) for qt, d in rows.items()}
    overall_src: dict[str, list[float]] = defaultdict(list)
    for d in rows.values():
        for m, v in d.items():
            overall_src[m].extend(v)
    overall = agg(overall_src)

    # For negatives there is no gold span to retrieve. What matters on Day 5 is
    # whether the system abstains, which needs a generator; what can be measured
    # here is how confidently retrieval returns *something* anyway -- the
    # distractor pressure an abstention decision has to survive.
    neg_scores = []
    for it in negatives:
        top = ix.search_dense(it.question, 1, vec=embed_one(it.question))
        if top:
            neg_scores.append(top[0][1])
    neg_summary = {
        "n": len(negatives),
        "nearest_clause_cosine_distance": {
            "median": round(statistics.median(neg_scores), 4) if neg_scores else None,
            "min": round(min(neg_scores), 4) if neg_scores else None,
        },
        "note": "no gold span exists; Day 5 measures abstention, not recall, on these",
    }

    report = {
        "golden": str(golden),
        "index": str(index),
        "k": k,
        "items": len(items),
        "grounded": len(grounded),
        "overall": overall,
        "per_query_type": per_type,
        "negatives": neg_summary,
        "saturation_ceiling": SATURATION_CEILING,
        "saturated": overall.get(f"bm25_hit@{k}", 0) > SATURATION_CEILING
        and overall.get(f"dense_hit@{k}", 0) > SATURATION_CEILING,
    }

    w = max(len(q) for q in per_type) + 2
    print(
        f"{'query_type':{w}}  {'bm25 hit@' + str(k):>12} {'dense hit@' + str(k):>12} "
        f"{'bm25 full@' + str(k):>12} {'dense full@' + str(k):>12}  n"
    )
    for qt, d in sorted(per_type.items()):
        print(
            f"{qt:{w}}  {d[f'bm25_hit@{k}']:12.3f} {d[f'dense_hit@{k}']:12.3f} "
            f"{d[f'bm25_full@{k}']:12.3f} {d[f'dense_full@{k}']:12.3f}  "
            f"{len(rows[qt][f'bm25_hit@{k}'])}"
        )
    print(
        f"{'OVERALL':{w}}  {overall[f'bm25_hit@{k}']:12.3f} {overall[f'dense_hit@{k}']:12.3f} "
        f"{overall[f'bm25_full@{k}']:12.3f} {overall[f'dense_full@{k}']:12.3f}  {len(grounded)}"
    )
    print()
    if report["saturated"]:
        print(
            f"SATURATED: both arms exceed {SATURATION_CEILING:.0%} hit@{k}. Day 5 cannot "
            "distinguish configurations against this set."
        )
        print(
            "Remedy is to ADD contested and multi-hop items, never to remove items a "
            "baseline answered."
        )
    else:
        print(f"Headroom present: neither arm exceeds {SATURATION_CEILING:.0%} hit@{k}.")

    if out:
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"report -> {out}")
    # The gate never fails a build. A saturated set is a finding to act on, not
    # a broken file, and returning non-zero here would tempt exactly the fix
    # this module exists to forbid.
    return 0
