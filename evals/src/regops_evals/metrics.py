"""Ranking metrics as pure functions, because a metric bug is invisible.

A wrong retriever shows up as a bad number. A wrong *metric* shows up as a good
number, in every cell, consistently, and nothing downstream can detect it. So
these take two lists and return a float, they touch no index and no model, and
every one of them is tested against values worked out by hand -- including the
degenerate cases that produce plausible-looking wrong answers: nothing
retrieved, everything retrieved, gold at rank 1, fewer results than k, and the
same clause appearing twice in one ranking.

**Duplicates.** In the parent-child ablation the retrieval unit is the chunk, so
a ranking can name the same clause four times. The rule here is that a repeat
neither helps nor is silently removed: the list is truncated at `k` as it was
actually returned, the set tests run over what is inside that window, and nDCG
credits a clause once. Deduplicating before truncation would hand the chunk
configuration five *distinct* clauses it never retrieved, and would make the
ablation measure the metric instead of the system.

**What nDCG can say here.** Labels are binary and 45 of the 115 grounded items
have exactly one gold span. For those, nDCG@10 is a monotone function of the
gold rank and carries the same information as MRR -- it is genuinely independent
evidence only on the multi-span types (`multi_hop`, `comparative`). Both are
reported; the write-up says this once and does not narrate a single-span nDCG
movement as if it were a second finding.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def hit_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """1.0 if *any* gold span is in the top k. Day 4's `hit@k`, unchanged."""
    return 1.0 if (gold & set(ranked[:k])) else 0.0


def recall_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """Fraction of gold spans inside the top k.

    Between `hit@k` (any) and `full@k` (all), and the only one of the three that
    distinguishes "one hop of two" from "neither hop" -- which is most of what
    the multi-span types do.
    """
    if not gold:
        return 0.0
    return len(gold & set(ranked[:k])) / len(gold)


def full_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """1.0 only if *every* gold span is in the top k.

    The honest bar for a hop: retrieving one half does not answer it.
    """
    return 1.0 if gold and gold <= set(ranked[:k]) else 0.0


def mrr(ranked: Sequence[str], gold: set[str]) -> float:
    """Reciprocal rank of the first gold span, 0.0 if none is retrieved."""
    for i, uid in enumerate(ranked, 1):
        if uid in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], gold: set[str], k: int) -> float:
    """Binary-gain nDCG. A clause already credited scores 0 if it repeats."""
    if not gold:
        return 0.0
    dcg = 0.0
    seen: set[str] = set()
    for i, uid in enumerate(ranked[:k], 1):
        if uid in gold and uid not in seen:
            seen.add(uid)
            dcg += 1.0 / math.log2(i + 1)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile. `p` in [0, 100].

    Nearest-rank rather than interpolated so a reported p95 is a latency some
    query actually had, which is what a latency budget is stated against.
    """
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, math.ceil(p / 100 * len(s)) - 1)
    return s[idx]


# The eight columns every configuration reports, in table order.
RETRIEVAL_METRICS = ("hit@5", "recall@5", "full@5", "hit@20", "ndcg@10", "mrr", "p50_s", "p95_s")


def score_ranking(ranked: Sequence[str], gold: set[str]) -> dict[str, float]:
    """Every rank-based metric for one query. Latency is added by the harness."""
    return {
        "hit@1": hit_at_k(ranked, gold, 1),
        "hit@5": hit_at_k(ranked, gold, 5),
        "hit@20": hit_at_k(ranked, gold, 20),
        "recall@5": recall_at_k(ranked, gold, 5),
        "recall@20": recall_at_k(ranked, gold, 20),
        "full@5": full_at_k(ranked, gold, 5),
        "full@20": full_at_k(ranked, gold, 20),
        "ndcg@10": ndcg_at_k(ranked, gold, 10),
        "mrr": mrr(ranked, gold),
    }
