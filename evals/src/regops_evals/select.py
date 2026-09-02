"""Choosing what to ask about, before anything is asked.

Candidate selection is where a golden set's difficulty is decided, and it is the
step most benchmarks skip -- sample uniformly, generate, and discover afterwards
that every question was easy. Day 4's research found exactly that: questions
generated from randomly drawn clauses gave BM25 92% recall@5, at ceiling before
any retrieval variant was applied.

So selection is stratified by **how crowded a clause's neighbourhood is**. MAS
publishes near-identical AML/CFT notices per regulated entity class -- 25 of
them in this corpus -- so a clause can have a dozen near-twins that differ only
in whom they bind. Sampling deliberately across isolated, moderate and contested
regions is what gives Day 5 something to measure.

The one thing selection must never do is look at retrieval results. Gold spans
are fixed here, before any retriever runs, or the ground truth becomes a
function of the system under test.
"""

from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass, field

from regops_evals.corpus import (
    AMENDMENT_RE,
    DELETED_RE,
    XREF_NOTICE_PARA,
    XREF_PARA_OF,
    XREF_THE_NOTICE,
    Clause,
    Index,
)
from regops_evals.schema import QueryType

# Difficulty bands, by count of near-duplicate clauses within cosine 0.10 in
# *other* documents. The boundaries come from the measured distribution over a
# 600-clause sample, not from taste.
BANDS = {"isolated": (0, 0), "moderate": (1, 4), "contested": (5, 999)}

# Maximum cosine distance between any two clauses in a comparative group. A
# shared clause number does not mean a shared topic (see `select_comparative`),
# so this is what actually decides whether a comparison is well posed.
ALIGNMENT_MAX = 0.25

# Pool sizes: how many clauses get a near-duplicate count computed (0.09s each)
# before the stratified draw. Larger than the target so each band can be filled.
POOL = 900


@dataclass
class Candidate:
    """One selected question-to-be, with its gold spans already fixed."""

    query_type: QueryType
    clauses: list[Clause]
    near_dups: int = 0
    band: str = "isolated"
    entity: str | None = None
    # Type-specific material the generator needs: the amendment text, the
    # cross-reference that was resolved, the sibling entity classes.
    hint: dict = field(default_factory=dict)

    @property
    def primary(self) -> Clause:
        return self.clauses[0]


def _band(n: int) -> str:
    for name, (lo, hi) in BANDS.items():
        if lo <= n <= hi:
            return name
    return "contested"


def _score_pool(ix: Index, clauses: list[Clause], rng: random.Random, size: int) -> list[Candidate]:
    """Draw `size` clauses and measure each one's crowding."""
    pool = clauses[:]
    rng.shuffle(pool)
    out = []
    for c in pool[:size]:
        n = len(ix.near_duplicates(c.doc_id, c.section_path))
        out.append(Candidate("factual_lookup", [c], near_dups=n, band=_band(n), entity=c.entity))
    return out


def select_factual(ix: Index, n: int, rng: random.Random, pool: list[Candidate]) -> list[Candidate]:
    """Split evenly across the three difficulty bands, and across doc_type inside each.

    An even split is the point. A uniform sample of this corpus is mostly
    isolated clauses, which is how a set ends up saturated.
    """
    per_band = n // len(BANDS)
    out: list[Candidate] = []
    for band in BANDS:
        got = [c for c in pool if c.band == band]
        rng.shuffle(got)
        # Interleave notices and guidelines so one doc_type cannot dominate a band.
        notices = [c for c in got if c.primary.doc_type == "notices"]
        guides = [c for c in got if c.primary.doc_type == "guidelines"]
        mixed: list[Candidate] = []
        while (notices or guides) and len(mixed) < per_band + 5:
            if notices:
                mixed.append(notices.pop())
            if guides:
                mixed.append(guides.pop())
        out.extend(mixed[:per_band])
    # Any shortfall (a band with too few members) is topped up from the rest.
    rest = [c for c in pool if c not in out]
    rng.shuffle(rest)
    out.extend(rest[: max(0, n - len(out))])
    return out[:n]


def resolve_xrefs(ix: Index) -> list[tuple[Clause, Clause, str]]:
    """Every cross-reference where **both** ends resolve to a real clause.

    Two families, both measured: a guidelines document citing "paragraph X of the
    Notice" it annotates (467 hops, 120 distinct sources), and an explicit
    "paragraph X of MAS Notice NNN" (129 hops, 46 sources). An unresolvable
    reference is not made into a question -- it is counted and reported, which is
    a finding about the corpus rather than a defect in the set.
    """
    clauses = ix.eligible_clauses()
    by_key = {(c.doc_id, c.section_path): c for c in clauses}
    codes = ix.code_map()
    parents = ix.guideline_parents()
    seen: set[tuple[str, str, str, str]] = set()
    out: list[tuple[Clause, Clause, str]] = []

    def add(src: Clause, tgt_doc: str, tgt_path: str, kind: str) -> None:
        tgt = by_key.get((tgt_doc, tgt_path))
        if tgt is None or tgt.doc_id == src.doc_id:
            return
        key = (src.doc_id, src.section_path, tgt.doc_id, tgt.section_path)
        if key not in seen:
            seen.add(key)
            out.append((src, tgt, kind))

    for c in clauses:
        if c.doc_id in parents:
            for m in XREF_THE_NOTICE.finditer(c.text):
                add(c, parents[c.doc_id], m.group(1), "guideline_to_notice")
        for m in XREF_PARA_OF.finditer(c.text):
            para, code = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip().upper()
            if doc := codes.get(code, {}).get("notices"):
                add(c, doc, para, "explicit_citation")
        for m in XREF_NOTICE_PARA.finditer(c.text):
            code, para = re.sub(r"\s+", " ", m.group(1)).strip().upper(), m.group(2)
            if doc := codes.get(code, {}).get("notices"):
                add(c, doc, para, "explicit_citation")
    return out


def select_multi_hop(ix: Index, n: int, rng: random.Random) -> list[Candidate]:
    """Pairs where a question needs both the citing clause and the cited one."""
    hops = resolve_xrefs(ix)
    rng.shuffle(hops)
    out, used_src = [], set()
    for src, tgt, kind in hops:
        # One item per source clause, so 30 items are 30 different questions.
        if src.section_uid in used_src:
            continue
        used_src.add(src.section_uid)
        out.append(
            Candidate(
                "multi_hop",
                [src, tgt],
                entity=src.entity or tgt.entity,
                hint={"hop_kind": kind, "cited_path": tgt.section_path},
            )
        )
        if len(out) >= n:
            break
    return out


def select_comparative(ix: Index, n: int, rng: random.Random) -> list[Candidate]:
    """The same requirement across parallel entity-class notices.

    MAS's 25 AML/CFT notices share a numbering scheme, which makes a shared
    `section_path` a cheap way to shortlist parallel clauses. It is **not**
    sufficient on its own, and assuming it was produced a real defect on the
    first pass: clause 11.7 is wire-transfer originator information in Notices
    824 and 1014, but correspondent accounts in Notice 626A. A question
    comparing those three "on wire transfers" compares two things and a third
    unrelated one, and the answer is nonsense.

    Measured over all 196 shared paths in the family, the median maximum
    pairwise cosine distance within a group is **0.330** -- so most shared paths
    are not parallel at all. Alignment is therefore checked with the vectors
    rather than assumed from the numbering: 73 groups fall within 0.25, which is
    ample for 25 items.
    """
    fam = {
        d for d, dt, t, _ in ix.documents() if dt == "notices" and "money laundering" in t.lower()
    }
    by_path: dict[str, list[Clause]] = {}
    for c in ix.eligible_clauses(obligations_only=True):
        if c.doc_id in fam and c.entity:
            by_path.setdefault(c.section_path, []).append(c)

    groups: list[tuple[str, list[Clause], float]] = []
    for path, cs in by_path.items():
        if len({c.entity for c in cs}) < 2:
            continue
        # One clause per entity class -- two copies of the same class is not a
        # comparison. Prefer three classes where the corpus offers them.
        by_entity: dict[str, Clause] = {}
        for c in cs:
            by_entity.setdefault(c.entity or "", c)
        picked = list(by_entity.values())[:3]
        vecs = [ix.clause_vector(c.doc_id, c.section_path) for c in picked]
        if len(picked) < 2 or any(v is None for v in vecs):
            continue
        spread = max(
            float(
                ix.conn.execute(
                    "SELECT array_cosine_distance(?::FLOAT[768], ?::FLOAT[768])", [a, b]
                ).fetchone()[0]
            )
            for a, b in itertools.combinations(vecs, 2)
        )
        if spread <= ALIGNMENT_MAX:
            groups.append((path, picked, spread))

    rng.shuffle(groups)
    out = [
        Candidate(
            "comparative",
            picked,
            entity=None,
            hint={
                "shared_path": path,
                "entities": [c.entity for c in picked],
                "texts_differ": len({" ".join(c.text.split())[:400] for c in picked}) > 1,
                "alignment": round(spread, 4),
            },
        )
        for path, picked, spread in groups
    ]
    # Aim for two-thirds differing, one-third identical -- both are real
    # questions, and a set of only-differing pairs would never test whether the
    # system can say "the same duty applies to both". Whichever side runs out,
    # the other backfills, so the target count is met before the mix is.
    diff = [c for c in out if c.hint["texts_differ"]]
    same = [c for c in out if not c.hint["texts_differ"]]
    want_same = min(len(same), n - (n * 2) // 3)
    picked_out = diff[: n - want_same] + same[:want_same]
    if len(picked_out) < n:
        rest = [c for c in out if c not in picked_out]
        picked_out += rest[: n - len(picked_out)]
    return picked_out[:n]


def select_temporal(ix: Index, n: int, rng: random.Random) -> list[Candidate]:
    """Stated-time questions, from what the documents actually record.

    Not version diffs: 0 documents in this corpus have more than one version row,
    and inventing a pair would be exactly the fake `regdocs-mcp` ADR-004 refused
    to ship. Three real sources: amendment-history endnotes, `[Deleted by ...]`
    markers, and clauses that state their own commencement.
    """
    clauses = ix.eligible_clauses()
    buckets: dict[str, list[Candidate]] = {"amendment": [], "deleted": [], "effect": []}
    for c in clauses:
        if m := AMENDMENT_RE.search(c.text):
            buckets["amendment"].append(
                Candidate(
                    "temporal",
                    [c],
                    entity=c.entity,
                    hint={
                        "kind": "amendment",
                        "instrument": m.group(1).strip(),
                        "effect_from": m.group(2),
                    },
                )
            )
        elif m := DELETED_RE.search(c.text):
            buckets["deleted"].append(
                Candidate(
                    "temporal",
                    [c],
                    entity=c.entity,
                    hint={"kind": "deleted", "by": m.group(1).strip()},
                )
            )
        elif re.search(r"with effect from\s+\d{1,2}\s+\w+\s+\d{4}", c.text, re.I):
            buckets["effect"].append(
                Candidate("temporal", [c], entity=c.entity, hint={"kind": "commencement"})
            )
    out: list[Candidate] = []
    for name in ("amendment", "deleted", "effect"):
        rng.shuffle(buckets[name])
        out.extend(buckets[name][: (n + 2) // 3])
    rng.shuffle(out)
    return out[:n]


def select_negative_seeds(ix: Index, n: int, rng: random.Random) -> list[Candidate]:
    """Seeds for unanswerable questions -- topical, so they are not nonsense.

    A negative set made of gibberish measures nothing: any retriever returns
    nothing for gibberish. These have to be questions a compliance officer would
    plausibly ask, which is why each is seeded with a real topic from the corpus
    and then pushed out of scope along one of five named axes.
    """
    from regops_evals.schema import AbsenceReason  # noqa: F401  (documented in schema)

    reasons = [
        "other_jurisdiction",
        "out_of_scope_instrument",
        "withdrawn_requirement",
        "invented_specific",
        "unregulated_topic",
    ]
    docs = [(d, t) for d, dt, t, _ in ix.documents() if dt == "notices"]
    rng.shuffle(docs)
    out = []
    for i in range(n):
        doc_id, title = docs[i % len(docs)]
        out.append(
            Candidate(
                "negative",
                [],
                hint={"absence_reason": reasons[i % len(reasons)], "topic_title": title},
            )
        )
    return out


def select_all(ix: Index, targets: dict, seed: int = 0) -> dict[str, list[Candidate]]:
    rng = random.Random(seed)
    # `factual_lookup` and `comparative` want clauses that state a duty; the
    # other three types are grounded in clauses that legitimately do not.
    pool = _score_pool(ix, ix.eligible_clauses(obligations_only=True), rng, POOL)
    return {
        "factual_lookup": select_factual(ix, targets["factual_lookup"], rng, pool),
        "multi_hop": select_multi_hop(ix, targets["multi_hop"], rng),
        "comparative": select_comparative(ix, targets["comparative"], rng),
        "temporal": select_temporal(ix, targets["temporal"], rng),
        "negative": select_negative_seeds(ix, targets["negative"], rng),
    }
