"""The agent's tool surface: the portable one, and the measured one.

The prep plan mandates an agent over `regdocs-mcp`, and that is the deliverable
-- a tool surface any MCP host can call. Day 6's research measured what it costs.
`search_notices` is BM25 over section text and nothing else, because the server
repo must stay a `uv sync` from green CI without a multi-gigabyte CUDA download
(ADR-001, ADR-013). Day 5 measured that arm as the *bottom* rung of its ladder:

    C1 BM25                    hit@5 0.670   MRR 0.486   <- what search_notices does
    C4 hybrid + cross-encoder  hit@5 0.835   MRR 0.681   <- what regops-retrieval does

So routing the agent through the portable tool costs 0.165 hit@5 and 0.195 MRR
against retrieval this workspace already has. That is not a defect in the server.
It is a tradeoff, and the point of giving the agent **both** tools is that the
tradeoff becomes a number measured on the same questions rather than an
architectural preference argued about. It also hands Day 8 two trajectories to
compare instead of one.

`search_local` is deliberately given the *same shape* as `search_notices` --
query in, ranked `(doc_id, section_path)` out, no full text -- so the only
variable between them is the retrieval behind the call. A tool that returned
richer results would confound the comparison with its own affordances.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import StructuredTool
from regops_retrieval.configs import LADDER, build
from regops_retrieval.index import Index
from regops_retrieval.rerank import CrossEncoder
from regops_retrieval.retrievers import QuestionVectors

# C4. Named by lookup rather than by index so a change to the ladder is a failure
# here rather than a silently different agent.
BEST = next(c for c in LADDER if c.name == "C4_hybrid_rerank")

# What one `search_local` call returns. `search_notices` defaults to 10 and the
# agent should not be able to tell the two apart by result count.
DEFAULT_TOP_K = 10

SEARCH_LOCAL_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Natural-language search text."},
        "top_k": {
            "type": "integer",
            "description": "How many clauses to return (1-50).",
            "default": DEFAULT_TOP_K,
        },
    },
    "required": ["query"],
}

SEARCH_LOCAL_DESCRIPTION = (
    "Hybrid search (BM25 + embeddings, cross-encoder reranked) across the same MAS "
    "notices and guidelines. Returns ranked clauses with their doc_id and section_path "
    "— not full text. Use get_document_section to read a result. Slower than "
    "search_notices and more accurate on questions where the wording of the question "
    "does not match the wording of the clause."
)


@dataclass
class LocalSearch:
    """C4, held open across an agent run.

    The cross-encoder is 1.33 GB and takes ~7s to load from the HF cache. Loading
    it per call would dominate every measurement taken through this tool, so it
    is loaded once and the object is the agent's for its lifetime.
    """

    index: Path
    top_k: int = DEFAULT_TOP_K

    def __post_init__(self) -> None:
        self._ix = Index(self.index)
        self._vectors = QuestionVectors(BEST.embed_model)
        self._retriever = build(BEST, self._ix, self._vectors, scorer=CrossEncoder())
        self.calls = 0

    def search(self, query: str, top_k: int | None = None) -> str:
        self.calls += 1
        k = int(top_k or self.top_k)
        hits = self._retriever.search(query, max(1, min(k, 50)))
        out = []
        for h in hits[:k]:
            cl = self._ix.clause_by_uid(h.section_uid)
            if cl is None:
                continue
            out.append(
                {
                    "doc_id": cl.doc_id,
                    "section_path": cl.section_path,
                    "title": cl.title,
                    "score": round(h.score, 6),
                    "snippet": " ".join(cl.text.split())[:320],
                }
            )
        return json.dumps({"hits": out, "total": len(out)}, indent=2)

    def close(self) -> None:
        self._ix.close()

    def as_tool(self) -> StructuredTool:
        def call(query: str, top_k: int = DEFAULT_TOP_K) -> str:
            return self.search(query, top_k)

        return StructuredTool.from_function(
            func=call,
            name="search_local",
            description=SEARCH_LOCAL_DESCRIPTION,
            args_schema=SEARCH_LOCAL_SCHEMA,
        )
