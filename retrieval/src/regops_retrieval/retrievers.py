"""Four arms and two combinators, all returning the same shape.

The point of the protocol is that fusion and reranking are not special cases.
`rrf(bm25, dense)` and `rerank(rrf(bm25, dense))` are ordinary values built from
ordinary values, which is what lets Day 5's seven configurations be seven
*declared objects* (`configs.py`) rather than seven flag combinations assembled
at a call site. If the table's rows and the code's objects are not literally
the same list, the table is a claim about code that may not exist.

Two things every arm here has to get right, both of which cost a day to learn:

- **A ranked list must be reproducible.** Ties are broken on the uid, in SQL,
  because DuckDB's parallel aggregation does not order tied rows consistently
  (ADR-022). Set metrics survived that; MRR and nDCG did not.
- **Query vectors are computed once.** They are bit-identical across calls, so
  caching removes an Ollama round trip from the latency of every dense config
  after the first without changing a single number. The cache is explicit rather
  than an `lru_cache` so that a benchmark can *exclude* it and measure the cold
  path, which is what Day 5's latency column actually reports.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from regops_retrieval.index import EMBED_MODEL, Index, embed_one

# Published default from Cormack et al. 2009. Left at 60 and *not* tuned: with
# 115 grounded items, fitting a fusion constant on the same set the table is
# read off would be fitting noise and calling it a result (ADR-020).
RRF_K = 60


@dataclass(frozen=True, slots=True)
class Scored:
    """One result. `uid` is what was retrieved; `section_uid` is what is scored.

    They differ only in chunk mode, where a clause can appear more than once.
    Metrics always read `section_uid` -- gold spans are clauses -- and context
    assembly always reads `uid`, which is the whole difference the parent-child
    ablation measures.
    """

    uid: str
    section_uid: str
    score: float
    rank: int


class Retriever(Protocol):
    name: str

    def search(self, question: str, k: int) -> list[Scored]: ...


class QuestionVectors:
    """Query embeddings, computed once per run and reused by every dense config.

    Cold-path timing is what the benchmark reports, so `embed_seconds` records
    what the first computation cost and the harness adds it back.
    """

    def __init__(self, ix_model: str = EMBED_MODEL) -> None:
        self.model = ix_model
        self._vecs: dict[str, list[float]] = {}
        self.embed_seconds: dict[str, float] = {}
        # (question, was_cache_hit) for everything requested since `reset()`.
        self.touched: list[tuple[str, bool]] = []

    def __len__(self) -> int:
        return len(self._vecs)

    def get(self, question: str) -> list[float]:
        hit = question in self._vecs
        if not hit:
            import time

            t0 = time.perf_counter()
            self._vecs[question] = embed_one(question, model=self.model)
            self.embed_seconds[question] = time.perf_counter() - t0
        self.touched.append((question, hit))
        return self._vecs[question]

    def cost(self, question: str) -> float:
        """The measured seconds the first embed of this question took."""
        return self.embed_seconds.get(question, 0.0)

    def reset(self) -> None:
        self.touched = []

    def replay_cost(self) -> float:
        """Embed seconds this query would have paid without the cache.

        The cache exists to remove a confound, not to flatter the latency
        column: an embed served from it is added back at the price the first
        one cost, so a dense config's reported p50 is the cold path either way.
        """
        return sum(self.cost(q) for q, hit in self.touched if hit)

    def warm(self, questions: Iterable[str]) -> None:
        for q in questions:
            self.get(q)


def _rank(pairs: list[tuple[str, str, float]]) -> list[Scored]:
    return [Scored(uid, sec, score, i + 1) for i, (uid, sec, score) in enumerate(pairs)]


@dataclass
class Bm25:
    """Lexical, over clause text. The Day 3 FTS index, unchanged."""

    ix: Index
    unit: str = "clause"
    name: str = "bm25"

    def search(self, question: str, k: int) -> list[Scored]:
        if self.unit == "chunk":
            return _rank(self.ix.search_bm25_chunks(question, k))
        return _rank([(u, u, s) for u, s in self.ix.search_bm25(question, k)])


@dataclass
class Dense:
    """Vector, over chunk embeddings, rolled up to the parent clause by default.

    `model` selects the arm: the plain embeddings, or the `+ctx` ones written
    over context-prepended chunk text (ADR-015). Scores are returned as
    similarity (1 - cosine distance) so that fusion and reporting never have to
    remember which direction is better.
    """

    ix: Index
    vectors: QuestionVectors
    model: str = EMBED_MODEL
    unit: str = "clause"
    name: str = "dense"

    def search(self, question: str, k: int) -> list[Scored]:
        vec = self.vectors.get(question)
        if self.unit == "chunk":
            rows = self.ix.search_dense_chunks(question, k, vec=vec, model=self.model)
            return _rank([(c, s, 1.0 - d) for c, s, d in rows])
        rows2 = self.ix.search_dense(question, k, vec=vec, model=self.model)
        return _rank([(u, u, 1.0 - d) for u, d in rows2])


@dataclass
class Rrf:
    """Reciprocal rank fusion. Four lines, every one easy to get subtly wrong.

    Score is `sum over arms of 1/(k + rank)`. An item missing from an arm
    contributes nothing -- it does not contribute `1/(k + len+1)`, which is the
    usual mistake and quietly rewards short result lists. Ties fuse
    deterministically because each arm's input order already does, and the final
    sort breaks equal scores on the uid.
    """

    arms: tuple[Retriever, ...]
    k: int = RRF_K
    name: str = "rrf"

    def search(self, question: str, k: int) -> list[Scored]:
        # Fuse over a deeper pool than is returned: an item ranked 40th in one
        # arm and 3rd in another should be able to surface.
        pool = max(k, 50)
        acc: dict[str, float] = {}
        sec: dict[str, str] = {}
        for arm in self.arms:
            for h in arm.search(question, pool):
                acc[h.uid] = acc.get(h.uid, 0.0) + 1.0 / (self.k + h.rank)
                sec.setdefault(h.uid, h.section_uid)
        order = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return _rank([(u, sec[u], s) for u, s in order])


class Scorer(Protocol):
    """A cross-encoder, or a stub standing in for one in a test."""

    def score(self, question: str, passages: list[str]) -> list[float]: ...


@dataclass
class Rerank:
    """Reorder a base ranking by a cross-encoder over the retrieved text.

    `top_n` is the number of candidates scored, not the number returned: the
    whole pool is reordered and the caller truncates. Stated as an untuned
    constant -- 50 is what the base arms return, and scoring all of them costs
    ~350ms on the 3090, which the day's budget can absorb (ADR-020).

    Reranking a pool it does not extend cannot change recall at the pool depth.
    That is a property of the design, not a null result, and the table says so
    where recall@20 moves by zero.
    """

    base: Retriever
    scorer: Scorer
    text_of: object  # Callable[[Scored], str]
    top_n: int = 50
    name: str = "rerank"

    def search(self, question: str, k: int) -> list[Scored]:
        pool = self.base.search(question, max(k, self.top_n))
        cand, tail = pool[: self.top_n], pool[self.top_n :]
        if not cand:
            return []
        texts = [self.text_of(h) for h in cand]  # type: ignore[operator]
        scores = self.scorer.score(question, texts)
        order = sorted(zip(cand, scores, strict=True), key=lambda hs: (-hs[1], hs[0].uid))
        merged = [(h.uid, h.section_uid, float(s)) for h, s in order]
        # Anything below the reranked window keeps its base order, below every
        # reranked item, so the returned list stays a total order over the pool.
        floor = min((s for _, _, s in merged), default=0.0)
        merged += [(h.uid, h.section_uid, floor - h.rank) for h in tail]
        return _rank(merged[:k])


@dataclass
class Decomposed:
    """Run the base retriever on sub-questions and fuse the results by RRF.

    The original question is always one of the sub-queries: decomposition that
    can only lose information is a strictly worse retriever, and the failure
    mode being measured is the *cost* of decomposing questions that did not need
    it, not the cost of throwing the question away.
    """

    base: Retriever
    decompose: object  # Callable[[str], list[str]]
    k: int = RRF_K
    name: str = "decomposed"

    def search(self, question: str, k: int) -> list[Scored]:
        subs = [question] + [s for s in self.decompose(question) if s != question]  # type: ignore[operator]
        pool = max(k, 50)
        acc: dict[str, float] = {}
        sec: dict[str, str] = {}
        for sub in subs:
            for h in self.base.search(sub, pool):
                acc[h.uid] = acc.get(h.uid, 0.0) + 1.0 / (self.k + h.rank)
                sec.setdefault(h.uid, h.section_uid)
        order = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return _rank([(u, sec[u], s) for u, s in order])
