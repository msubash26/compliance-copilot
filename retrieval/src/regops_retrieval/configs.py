"""The seven configurations, as objects rather than as flag combinations.

The prep plan's list -- "dense · BM25 · hybrid RRF · hybrid + cross-encoder
rerank · contextual on/off · parent-child on/off · query decomposition on/off"
-- is not seven things if it is read as a factorial. It is 4 x 2 x 2 x 2 = 32,
and 32 rows over 115 grounded items is a table nobody can read and every cell of
which is thin.

So it is read as a **ladder plus ablations**, which is the only reading in which
an ablation means anything, because an ablation needs a fixed reference:

    C1 bm25  ->  C2 dense  ->  C3 hybrid RRF  ->  C4 hybrid + rerank
                                                    |
                              C5 (contextual off) · C6 (parent-child off) · C7 (decomposition on)

Every rung carries contextual embeddings on and parent-child on. C5 and C6 turn
one of those off against C4. C7 is the one that reads backwards -- decomposition
is off on the whole ladder, so the ablation turns it *on* -- and it is still an
ablation in the sense that matters: one switch, moved against a fixed reference.

`rung=True` is what selects the four configurations that get generation metrics
(ADR-021). It lives here, next to the configuration it describes, so that
"which rows have groundedness numbers" is a property of the declared list and
not of an argument someone passed on the day.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from regops_retrieval.index import CTX_EMBED_MODEL, EMBED_MODEL, Index
from regops_retrieval.retrievers import (
    Bm25,
    Decomposed,
    Dense,
    QuestionVectors,
    Rerank,
    Retriever,
    Rrf,
    Scored,
    Scorer,
)

# The pool every configuration ranks. Fixed across all seven so that C4's
# reranker reorders the same candidate set C3 returns -- otherwise C3 -> C4
# would differ in two ways at once and the rerank column would be unreadable.
POOL = 50


@dataclass(frozen=True)
class Config:
    name: str
    label: str
    arms: str  # bm25 | dense | hybrid
    rung: bool
    contextual: bool = True
    parent_child: bool = True
    rerank: bool = False
    decompose: bool = False
    note: str = ""

    @property
    def unit(self) -> str:
        return "clause" if self.parent_child else "chunk"

    @property
    def context_mode(self) -> str:
        return "parent" if self.parent_child else "child"

    @property
    def embed_model(self) -> str:
        return CTX_EMBED_MODEL if self.contextual else EMBED_MODEL


LADDER: tuple[Config, ...] = (
    Config(
        name="C1_bm25",
        label="BM25 only",
        arms="bm25",
        rung=True,
        note="the Day 4 baseline arm; reproduces golden/v1/saturation.json",
    ),
    Config(
        name="C2_dense",
        label="Dense only (+ctx)",
        arms="dense",
        rung=True,
        note="contextual embeddings, rolled up to the parent clause",
    ),
    Config(
        name="C3_hybrid_rrf",
        label="Hybrid RRF",
        arms="hybrid",
        rung=True,
        note="RRF k=60 over BM25 and dense+ctx",
    ),
    Config(
        name="C4_hybrid_rerank",
        label="Hybrid RRF + cross-encoder",
        arms="hybrid",
        rung=True,
        rerank=True,
        note="bge-reranker-v2-m3 reorders the 50-candidate pool",
    ),
)

ABLATIONS: tuple[Config, ...] = (
    Config(
        name="C5_no_context",
        label="C4, contextual off",
        arms="hybrid",
        rung=False,
        rerank=True,
        contextual=False,
        note="plain chunk embeddings; isolates ADR-015's contribution",
    ),
    Config(
        name="C6_child_units",
        label="C4, parent-child off",
        arms="hybrid",
        rung=False,
        rerank=True,
        parent_child=False,
        note="chunks are the retrieval and assembly unit; expected flat on recall",
    ),
    Config(
        name="C7_decompose",
        label="C4 + query decomposition",
        arms="hybrid",
        rung=False,
        rerank=True,
        decompose=True,
        note="the one ablation that adds rather than removes a switch",
    ),
)

# Not part of the published table, and deliberately so: a diagnostic exists to
# support a claim made elsewhere, not to add a row. `D1_dense_plain` is C2 with
# contextual embeddings off, which is the only way to isolate ADR-015's
# contribution *without* the cross-encoder on top of it -- and the reason that
# matters is that C4 vs C5 says contextual is worth +0.9 MRR, while the dense
# arm alone says it is worth several times that. Both are true, and the pair is
# the finding.
DIAGNOSTICS: tuple[Config, ...] = (
    Config(
        name="D1_dense_plain",
        label="C2 with contextual off (diagnostic)",
        arms="dense",
        rung=False,
        contextual=False,
        note="isolates ADR-015 on the dense arm, with no reranker to absorb it",
    ),
)

CONFIGS: tuple[Config, ...] = LADDER + ABLATIONS
BY_NAME = {c.name: c for c in CONFIGS + DIAGNOSTICS}


def build(
    cfg: Config,
    ix: Index,
    vectors: QuestionVectors,
    *,
    scorer: Scorer | None = None,
    decompose_dir: Path | None = None,
) -> Retriever:
    """Assemble one configuration's retriever.

    `scorer` is injected rather than loaded here so a test can drive the whole
    rerank pipeline with a stub, and so the 1.33 GB of weights are loaded once
    per process rather than once per configuration.
    """
    bm25 = Bm25(ix, unit=cfg.unit)
    dense = Dense(ix, vectors, model=cfg.embed_model, unit=cfg.unit)

    base: Retriever
    if cfg.arms == "bm25":
        base = bm25
    elif cfg.arms == "dense":
        base = dense
    else:
        base = Rrf((bm25, dense))

    if cfg.rerank:
        if scorer is None:
            raise ValueError(f"{cfg.name} reranks and no scorer was supplied")
        base = Rerank(base, scorer, _text_of(ix, cfg.context_mode), top_n=POOL)

    if cfg.decompose:
        from regops_retrieval.decompose import Decomposer

        if decompose_dir is None:
            raise ValueError(f"{cfg.name} decomposes and no cache directory was supplied")
        base = Decomposed(base, Decomposer(decompose_dir))

    return base


def _text_of(ix: Index, mode: str) -> Callable[[Scored], str]:
    """What the cross-encoder actually reads for a hit.

    Truncated at 4,000 characters before tokenisation: the model's pair window
    is 512 tokens, and handing it a 127,564-character clause costs tokenizer
    time for text it will discard.
    """

    def parent(h: Scored) -> str:
        cl = ix.clause_by_uid(h.section_uid)
        return (cl.text if cl else "")[:4000]

    def child(h: Scored) -> str:
        ch = ix.chunks([h.uid]).get(h.uid)
        return (ch.text if ch else parent(h))[:4000]

    return parent if mode == "parent" else child
