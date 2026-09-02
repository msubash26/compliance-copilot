"""The retrieval sweep: seven configurations, one definition of search.

Every cell of the published table is an average over rows this module wrote to
`results/day5/raw/<config>.jsonl`, one per query per configuration, carrying the
ranking it scored and the latency it took. That is the difference between a
results table and a screenshot: any number in it can be traced back to the
queries that produced it, and a surprising cell can be opened rather than
argued about.

Three things this harness refuses to do:

- **Sample.** All seven configurations run all 150 items. Retrieval metrics cost
  about four minutes in total, so there is no reason to quote a cell from a
  subset and every reason not to.
- **Redefine search.** The arms come from `regops_retrieval`, which is the same
  code the Day 4 gate now calls and the same code Day 6's agent will call. C1's
  row is checked against `golden/v1/saturation.json` before any other number is
  believed; a mismatch means the definition moved and the table is void.
- **Hide the instrument's defects.** 28 of the 150 items are machine-verified
  but not human-reviewed. Every table is therefore computed twice -- over all
  150, and over the 122 unflagged -- and a conclusion that flips between them
  belongs to the golden set's noise, not to the retriever.
"""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from regops_retrieval.configs import BY_NAME, CONFIGS, POOL, Config, build
from regops_retrieval.context import assemble_context
from regops_retrieval.index import Index
from regops_retrieval.retrievers import QuestionVectors

from regops_evals.metrics import percentile, score_ranking
from regops_evals.schema import GoldenItem, read_jsonl

# Ranking metrics are undefined without a gold span, so the negatives are
# retrieved (their context feeds Phase 4's abstention test) and excluded from
# every recall/nDCG/MRR average. Latency is measured on all 150.
RANK_TYPES = ("factual_lookup", "multi_hop", "comparative", "temporal")


@dataclass
class Row:
    """One query under one configuration. Written verbatim to the raw JSONL."""

    config: str
    item_id: str
    query_type: str
    flagged: bool
    gold: list[str]
    ranked: list[str]  # section_uids in rank order, top 20, duplicates kept
    latency_s: float
    embed_replay_s: float
    decompose_s: float
    context_chars: int
    context_truncated: int
    context_dropped: int
    metrics: dict[str, float] = field(default_factory=dict)


def run_config(
    cfg: Config,
    items: list[GoldenItem],
    ix: Index,
    vectors: QuestionVectors,
    *,
    scorer=None,
    decompose_dir: Path | None = None,
    context: bool = True,
) -> list[Row]:
    """Run one configuration over the whole set and return per-item rows."""
    retriever = build(cfg, ix, vectors, scorer=scorer, decompose_dir=decompose_dir)
    decomposer = getattr(retriever, "decompose", None)
    rows: list[Row] = []

    for it in items:
        vectors.reset()
        t0 = time.perf_counter()
        hits = retriever.search(it.question, POOL)
        wall = time.perf_counter() - t0
        replay = vectors.replay_cost()
        dec_s = float(getattr(decomposer, "last_seconds", 0.0) or 0.0)

        ranked = [h.section_uid for h in hits[:20]]
        gold = {sp.section_uid for sp in it.gold_spans}

        asm = assemble_context(ix, hits, mode=cfg.context_mode) if context else None
        row = Row(
            config=cfg.name,
            item_id=it.id,
            query_type=it.query_type,
            flagged=it.verification.status == "flagged",
            gold=sorted(gold),
            ranked=ranked,
            # The cache removes a confound, not a cost: an embed it served is
            # added back at what the first one measured.
            latency_s=round(wall + replay, 4),
            embed_replay_s=round(replay, 4),
            decompose_s=round(dec_s, 4),
            context_chars=asm.chars if asm else 0,
            context_truncated=asm.truncated_excerpts if asm else 0,
            context_dropped=asm.dropped_excerpts if asm else 0,
            metrics=(
                {k: round(v, 6) for k, v in score_ranking(ranked, gold).items()} if gold else {}
            ),
        )
        rows.append(row)
    return rows


# -- aggregation ----------------------------------------------------------


def aggregate(rows: list[Row], *, unflagged_only: bool = False) -> dict:
    """Per-query-type and overall means, plus latency percentiles.

    Latency percentiles are computed over *all* 150 queries including the
    negatives -- a production p95 does not get to exclude the questions whose
    answer is "not in the corpus".
    """
    sel = [r for r in rows if not (unflagged_only and r.flagged)]
    by_type: dict[str, list[Row]] = defaultdict(list)
    for r in sel:
        by_type[r.query_type].append(r)

    def block(rs: list[Row]) -> dict[str, float]:
        rank_rows = [r for r in rs if r.metrics]
        out: dict[str, float] = {}
        if rank_rows:
            keys = rank_rows[0].metrics.keys()
            for m in keys:
                out[m] = round(statistics.mean(r.metrics[m] for r in rank_rows), 4)
        lat = [r.latency_s for r in rs]
        out["p50_s"] = round(percentile(lat, 50), 4)
        out["p95_s"] = round(percentile(lat, 95), 4)
        out["mean_context_chars"] = round(statistics.mean(r.context_chars for r in rs), 1)
        out["truncated_queries"] = sum(1 for r in rs if r.context_truncated or r.context_dropped)
        out["n"] = len(rs)
        out["n_ranked"] = len(rank_rows)
        return out

    return {
        "per_query_type": {qt: block(rs) for qt, rs in sorted(by_type.items())},
        "overall": block([r for r in sel if r.query_type in RANK_TYPES]),
        "all_items": block(sel),
    }


def run_sweep(
    golden: Path,
    index: Path,
    *,
    config_names: list[str] | None = None,
    raw_dir: Path = Path("results/day5/raw"),
    out: Path | None = None,
    baseline: Path | None = None,
) -> tuple[dict, dict[str, list[Row]]]:
    items = read_jsonl(golden)
    ix = Index(index)
    vectors = QuestionVectors()
    cfgs = [BY_NAME[n] for n in config_names] if config_names else list(CONFIGS)
    decompose_dir = Path("results/day5/decompositions")

    # Batch by model, or pay a 17.7 GB swap per query. C7 decomposes with
    # `qwen3.5:9b` and then embeds with `nomic-embed-text`; interleaved, Ollama
    # would evict and reload one of them 150 times over. So every decomposition
    # is taken first with the generator resident, then every query vector with
    # the embedder resident, and the sweep itself touches no model that is not
    # already warm. This is the Day 4 rule that cost `verify` a rewrite.
    if any(c.decompose for c in cfgs):
        from regops_retrieval.decompose import Decomposer

        dec = Decomposer(decompose_dir)
        t0 = time.perf_counter()
        subs: list[str] = []
        for n, it in enumerate(items, 1):
            subs += dec(it.question)
            if n % 50 == 0:
                print(f"  decomposed {n}/{len(items)}", flush=True)
        print(
            f"decompositions: {dec.calls} calls, {dec.hits} cached, {time.perf_counter() - t0:.0f}s"
        )
        vectors.warm(subs)

    t0 = time.perf_counter()
    vectors.warm(it.question for it in items)
    print(f"query vectors: {len(vectors)} embedded in {time.perf_counter() - t0:.0f}s")

    scorer = None
    if any(c.rerank for c in cfgs):
        from regops_retrieval import rerank as rr

        t0 = time.perf_counter()
        scorer = rr.load()
        print(f"cross-encoder {rr.MODEL_ID} on {scorer.device} in {time.perf_counter() - t0:.1f}s")

    raw_dir.mkdir(parents=True, exist_ok=True)
    all_rows: dict[str, list[Row]] = {}
    report: dict = {
        "golden": str(golden),
        "index": str(index),
        "items": len(items),
        "pool": POOL,
        "configs": {},
    }

    for cfg in cfgs:
        t0 = time.perf_counter()
        rows = run_config(
            cfg,
            items,
            ix,
            vectors,
            scorer=scorer,
            decompose_dir=decompose_dir,
        )
        wall = time.perf_counter() - t0
        all_rows[cfg.name] = rows
        path = raw_dir / f"{cfg.name}.jsonl"
        path.write_text("\n".join(json.dumps(asdict(r)) for r in rows) + "\n")
        report["configs"][cfg.name] = {
            "label": cfg.label,
            "note": cfg.note,
            "rung": cfg.rung,
            "switches": {
                "arms": cfg.arms,
                "contextual": cfg.contextual,
                "parent_child": cfg.parent_child,
                "rerank": cfg.rerank,
                "decompose": cfg.decompose,
            },
            "wall_s": round(wall, 1),
            "all_150": aggregate(rows),
            "unflagged_122": aggregate(rows, unflagged_only=True),
        }
        o = report["configs"][cfg.name]["all_150"]["overall"]
        print(
            f"{cfg.name:20s} hit@5 {o['hit@5']:.3f}  full@5 {o['full@5']:.3f}  "
            f"ndcg@10 {o['ndcg@10']:.3f}  mrr {o['mrr']:.3f}  "
            f"p50 {o['p50_s']:.3f}s  ({wall:.0f}s)",
            flush=True,
        )

    # Why a configuration lost is a different question from how much. This
    # compares where the first gold span *landed* under two configurations over
    # the items both retrieve it at all, which separates "found the wrong
    # documents" from "found the right ones and demoted them".
    if {"C4_hybrid_rerank", "C7_decompose"} <= set(all_rows):
        report["displacement"] = displacement(
            all_rows["C4_hybrid_rerank"], all_rows["C7_decompose"]
        )

    # The gate is a claim about C1 specifically. A run that does not include C1
    # has nothing to check, and printing FAIL there would cry wolf on every
    # diagnostic run until nobody read the line that matters.
    if baseline and baseline.exists() and "C1_bm25" in report["configs"]:
        report["baseline_gate"] = check_baseline(report, json.loads(baseline.read_text()))

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"report -> {out}")
    return report, all_rows


def _first_gold_rank(row: Row) -> int | None:
    gold = set(row.gold)
    return next((i for i, u in enumerate(row.ranked, 1) if u in gold), None)


def displacement(before: list[Row], after: list[Row]) -> dict:
    """Where the first gold span moved between two configurations."""
    b = {r.item_id: r for r in before}
    shifts: list[int] = []
    lost = 0
    for r in after:
        base = b.get(r.item_id)
        if base is None or not base.gold:
            continue
        ra, rb = _first_gold_rank(base), _first_gold_rank(r)
        if ra and rb:
            shifts.append(rb - ra)
        elif ra and not rb:
            lost += 1
    return {
        "before": before[0].config if before else "",
        "after": after[0].config if after else "",
        "n_both_retrieved": len(shifts),
        "mean_shift": round(statistics.mean(shifts), 2) if shifts else 0.0,
        "median_shift": statistics.median(shifts) if shifts else 0,
        "demoted": sum(1 for s in shifts if s > 0),
        "unchanged": sum(1 for s in shifts if s == 0),
        "promoted": sum(1 for s in shifts if s < 0),
        "dropped_out_of_top20": lost,
    }


# -- the sanity gate ------------------------------------------------------

# Day 4 published bm25 hit@5 = 0.670 over 115 grounded items. One item is 0.87
# points, so anything inside half an item is the same number; anything outside
# it means the sweep redefined search and every row below is void until that is
# explained.
BASELINE_TOLERANCE = 0.005


def check_baseline(report: dict, saturation: dict) -> dict:
    """C1's row must reproduce `golden/v1/saturation.json`, or nothing is believed."""
    checks = []
    c1 = report["configs"].get("C1_bm25")
    if c1:
        for metric, published in (
            ("hit@5", saturation["overall"]["bm25_hit@5"]),
            ("hit@20", saturation["overall"]["bm25_hit@20"]),
            ("full@5", saturation["overall"]["bm25_full@5"]),
        ):
            got = c1["all_150"]["overall"][metric]
            checks.append(
                {
                    "config": "C1_bm25",
                    "metric": metric,
                    "day4": published,
                    "day5": got,
                    "delta": round(got - published, 4),
                    "ok": abs(got - published) <= BASELINE_TOLERANCE,
                }
            )
    ok = all(c["ok"] for c in checks) if checks else False
    print("\nbaseline gate (Day 4 saturation.json vs Day 5 C1):")
    for c in checks:
        print(
            f"  {c['metric']:8s} day4 {c['day4']:.3f}  day5 {c['day5']:.3f}  "
            f"delta {c['delta']:+.4f}  {'OK' if c['ok'] else 'MISMATCH'}"
        )
    print("  PASS\n" if ok else "  FAIL — the harness changed what search means\n")
    return {"checks": checks, "passed": ok, "tolerance": BASELINE_TOLERANCE}
