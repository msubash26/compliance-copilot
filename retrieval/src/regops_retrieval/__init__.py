"""Retrieval over the regdocs index: four arms, two combinators, one reranker.

Day 5 moved these out of `regops_evals` so that the eval package does not own
the thing it evaluates, and so Day 6's agent can retrieve without importing an
eval harness. See ADR-020.
"""

from regops_retrieval.configs import ABLATIONS, CONFIGS, LADDER, Config, build
from regops_retrieval.context import CONTEXT_BUDGET, Assembled, assemble_context
from regops_retrieval.index import (
    CTX_EMBED_MODEL,
    DIM,
    EMBED_MODEL,
    Chunk,
    Clause,
    Index,
    base_url,
    embed_one,
)
from regops_retrieval.retrievers import (
    RRF_K,
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

__all__ = [
    "ABLATIONS",
    "CONFIGS",
    "CONTEXT_BUDGET",
    "CTX_EMBED_MODEL",
    "DIM",
    "EMBED_MODEL",
    "LADDER",
    "RRF_K",
    "Assembled",
    "Bm25",
    "Chunk",
    "Clause",
    "Config",
    "Decomposed",
    "Dense",
    "Index",
    "QuestionVectors",
    "Rerank",
    "Retriever",
    "Rrf",
    "Scored",
    "Scorer",
    "assemble_context",
    "base_url",
    "build",
    "embed_one",
]
