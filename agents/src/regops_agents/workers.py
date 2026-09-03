"""The five workers, and the one design choice that makes them worth having.

Day 6's finding, read off every failure the model owned: *tool selection was
correct in every single provocation; argument grounding is the defect.* F1 sets
a filter nobody asked for, F7 calls the right tool with an invented `doc_id`, F5
is handed a recovery path and ignores it. The pattern is the same each time --
the model knows which tool it wants and invents what to pass it.

So the supervisor's workers do not hand the model a tool and hope. **The model
supplies the one argument it is actually good at -- the search text -- and the
graph supplies every identifier.** `retrieve` calls `search_notices` with a query
the model wrote and a `top_k` the graph chose, and it reads sections with
`doc_id`s that came out of the search results, never out of the model.

That has a consequence worth stating plainly rather than claiming as a win: **F1
and F7 cannot occur here, because the capability that produces them has been
removed.** The cost is exactly the cost F1's prompt mitigation had -- the filters
are unavailable when a question genuinely wants one. This is a structural fix
with the same tradeoff as the prompt fix, not a better model.

Everything else is a single constrained-decoding call. Ollama's `format` measured
30/30 on shape in Day 6, so a worker that needs a small typed answer should ask
for one rather than parse prose. The exception is `check`, which calls no model
at all: layer 2 is a dictionary lookup, and spending a model call on something a
dictionary can decide is how a graph gets slow for no accuracy.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field
from regops_retrieval.index import Index

from regops_agents.llm import MODEL, chat
from regops_agents.structured import Answer, Citation, check_references, check_shape

# How many hits one retrieval round returns, and how many of them get read in
# full. Chosen, not model-supplied -- see the module docstring.
TOP_K = 8
READ_N = 5
SECTION_CHARS = 3000

# A coverage sweep needs *documents*, and eight hits on this corpus are often
# four clauses of the same notice. Asking for more hits is the cheap way to get
# more distinct documents; BM25 costs nothing next to a model call.
COVERAGE_TOP_K = 30

# Day 4's taxonomy, plus one route it does not have. Day 4 classified *questions*
# against a corpus; this classifies *tasks*, and "does this obligation appear
# across these documents" is a task shape rather than a question type. Adding it
# here rather than to Day 4's schema keeps the golden set's labels stable.
ROUTES = ("factual_lookup", "multi_hop", "comparative", "temporal", "negative", "coverage")


class Route(BaseModel):
    """The router's whole output. Small on purpose: it is one decision."""

    route: str = Field(description="One of: " + ", ".join(ROUTES))
    query: str = Field(description="The search text to look the answer up with")


class GroundedAnswer(BaseModel):
    """Day 6's `Answer`, with the one constraint Day 6 named and did not build.

    Day 6's dominant structured-output failure was **omission**: 10 of 11 invalid
    answers cited nothing at all, which layer 2 catches only by the roundabout
    route of "claims to be sufficient but cites nothing". The fix it named and
    deferred was a schema that cannot express an empty citation list, because
    that needs *two* schemas and something to choose between them. A supervisor
    has a router, so here it costs one branch.

    Measured: Ollama's constrained decoding honours `minItems`. Given a prompt
    with no sources at all it emits `[{"doc_id": "", "section_path": ""}]` rather
    than `[]` -- so the constraint does not conjure a real citation, it converts a
    **silent** omission into an **unresolvable** citation that layer 2 catches by
    its primary route. That is the whole gain, and it is worth stating in those
    terms rather than as "structured outputs fixed it".

    The cost is real and points the other way: on a question the corpus genuinely
    does not answer, this schema forces the model to write something in a field
    where nothing belongs. That is why `negative` routes keep the loose schema --
    abstention is a first-class outcome on this corpus, 35 of the 150 golden
    items have no answer in it, and forcing a citation there manufactures the
    fabrication Day 6's repair loop was removed for causing.
    """

    answer: str = Field(description="The answer, or why the corpus does not contain one")
    citations: list[Citation] = Field(
        min_length=1, description="At least one clause from an excerpt header"
    )
    sufficient: bool = Field(description="True if the context answers the question")


class Finding(BaseModel):
    """One document's verdict in a coverage sweep -- one fan-out branch's output."""

    covered: bool = Field(description="True if this document states such an obligation")
    section_path: str = Field(default="", description="The clause, if covered; else empty")
    quote: str = Field(default="", description="Up to 200 characters of the clause, if covered")


@dataclass
class Toolbox:
    """Everything a worker may reach outside the graph. Never enters state.

    Held in `config["configurable"]`, because it is a live MCP session and a
    DuckDB handle and neither is JSON. The checkpointer serialises state; a
    toolbox in state fails at the persistence boundary rather than here.
    """

    index: Path
    tools: dict = field(default_factory=dict)  # name -> StructuredTool, from the MCP server
    ix: Index | None = None
    model: str = MODEL

    def clause(self, doc_id: str, section_path: str):
        if self.ix is None:
            return None
        return self.ix.clause_by_uid(f"{doc_id}:{section_path}")


# -- 1. router ---------------------------------------------------------------

ROUTER_SYSTEM = (
    "You classify a compliance request and write the search text for it. Return JSON only."
)

ROUTER_PROMPT = """Classify this request into exactly one route:

- factual_lookup: one clause answers it
- multi_hop: the answer needs two or more clauses joined
- comparative: it asks how two things differ
- temporal: it asks when something applies or took effect
- negative: the corpus of MAS notices and guidelines almost certainly does not cover it
- coverage: it asks which documents do or do not address something

Then write the search text: the words most likely to appear in the clause itself,
not a restatement of the question.

REQUEST
{question}"""


def route(question: str, box: Toolbox) -> tuple[Route | None, dict]:
    """One call. Returns the route and what it cost."""
    reply = chat(
        ROUTER_PROMPT.format(question=question),
        system=ROUTER_SYSTEM,
        model=box.model,
        schema=Route.model_json_schema(),
    )
    try:
        r = Route.model_validate_json(reply.content)
    except Exception:  # noqa: BLE001 -- an unparseable route is a route decision
        return None, reply.spend()
    if r.route not in ROUTES:
        # Constrained decoding fixes the *shape*, not the *vocabulary* -- the
        # schema says "string", so an off-menu label is schema-valid. Day 6's F2
        # is the same distinction one layer up.
        r.route = "factual_lookup"
    return r, reply.spend()


# -- 2. retriever ------------------------------------------------------------


# The bridge truncates a tool result at 12,000 characters and appends a note
# saying so (Day 6's F3 mitigation, written for a *model* reading the text). A
# graph parsing the same string gets invalid JSON and, without this, zero hits and
# no error. Measured: `search_notices` crosses the cap at top_k 20 on this corpus.
TRUNCATED = "[truncated:"
MIN_TOP_K = 8


async def search(query: str, box: Toolbox, top_k: int) -> tuple[list[dict], list[str]]:
    """`search_notices`, backing off when the bridge truncates it out of being JSON.

    This is F14. It is not a bug in either layer: Day 6's cap is a correct
    mitigation for a model's context window, and the parse here is a correct way
    to read a JSON tool. The failure is that the cap was designed for a consumer
    that reads prose and is now being used by one that reads a grammar, and it
    fails **silently** -- zero hits, no exception, an answer that says the corpus
    is quiet. Backing off is the fix that keeps the portable surface; paging with
    the server's own `next_cursor` is the better one and is not free.
    """
    notes: list[str] = []
    k = top_k
    while True:
        raw = await box.tools["search_notices"].ainvoke({"query": query, "top_k": k})
        try:
            return json.loads(raw).get("hits", []), notes
        except (ValueError, AttributeError, TypeError):
            if TRUNCATED not in str(raw) or k <= MIN_TOP_K:
                notes.append(f"search: unparseable result at top_k={k} ({len(str(raw)):,} chars)")
                return [], notes
            k = max(MIN_TOP_K, k // 2)
            notes.append(f"search: result was truncated out of JSON, retrying at top_k={k}")


async def retrieve(query: str, box: Toolbox, *, top_k: int = TOP_K, read_n: int = READ_N):
    """Search, then read. Every identifier used here came out of a search result.

    No model call: the query was written by the router, and the arguments are the
    graph's. This is the node where Day 6's F1 and F7 are made impossible rather
    than discouraged.
    """
    hits, notes = await search(query, box, top_k)

    excerpts = []
    for h in hits[:read_n]:
        text = await box.tools["get_document_section"].ainvoke(
            {
                "doc_id": h["doc_id"],
                "section_path": h["section_path"],
                "max_chars": SECTION_CHARS,
            }
        )
        if str(text).startswith("TOOL ERROR"):
            # Recorded rather than skipped. A search hit that its own server
            # cannot then read is a contract problem between two tools, and a
            # silent `continue` turns it into "the corpus was quiet" three nodes
            # later -- which is the shape of every expensive afternoon.
            notes.append(f"read: {h['doc_id']}:{h['section_path']} — {str(text)[:120]}")
            continue
        excerpts.append(
            f"[{len(excerpts) + 1}] {h.get('title', '')} · clause {h['section_path']} "
            f"({h['doc_id']}:{h['section_path']})\n{text}"
        )
    return hits, "\n\n".join(excerpts), notes


# -- 3. obligation extractor -------------------------------------------------

EXTRACT_PROMPT = """Answer the question using only the numbered excerpts below.

Each excerpt's header is `[n] <title> · clause <path> (<doc_id>:<path>)`. When you cite,
`doc_id` is the 16-character hex string before the colon and `section_path` is what follows
it. Do not cite the excerpt number.

If the excerpts do not answer the question, set sufficient to false and say so.

QUESTION
{question}

EXCERPTS
{context}"""


def extract(
    question: str, context: str, box: Toolbox, *, route: str = "factual_lookup"
) -> tuple[Answer | None, dict]:
    """Day 6's prompt, unchanged. The schema is chosen by the route.

    `check_shape` still validates against the *loose* `Answer`, so a strict
    generation and a loose one are measured on the same yardstick and the rates
    stay comparable with Day 6's.
    """
    schema = Answer if route == "negative" else GroundedAnswer
    reply = chat(
        EXTRACT_PROMPT.format(question=question, context=context),
        model=box.model,
        schema=schema.model_json_schema(),
    )
    ans, _ = check_shape(reply.content)
    return ans, reply.spend()


# -- 4. gap analyst ----------------------------------------------------------

GAP_PROMPT = """DOCUMENT
{title}

CLAUSES FROM THIS DOCUMENT
{excerpt}

TOPIC
{topic}

Does any clause above place an obligation on the reader about that topic?

Answer only from the clauses shown. A clause that merely defines a term is not an
obligation. If one of them does state such an obligation, set covered to true, put its
clause number in section_path, and quote up to 200 characters of it. If none does, set
covered to false and leave the other fields empty. Do not infer, and do not answer from
what you know about this regulator."""


# What one branch puts in front of the model, and the window it is given to hold
# it. Both are explicit, and the second is why: Ollama sizes `num_ctx` for the
# request when it loads the model (32,768 here) and would silently front-truncate
# a prompt that outgrew it -- F3, which takes the system prompt and the topic
# before it touches the document. Pinning both makes the branch's behaviour a
# property of this code rather than of what the server happened to size.
BRANCH_CLAUSES = 6
BRANCH_CHARS = 20_000
BRANCH_NUM_CTX = 16_384

# Pages of a document's obligations a branch will read looking for its own
# topical clauses, and how many topic words a clause must contain to be one.
# Two rather than one: "person" alone matches most of an AML notice.
MAX_PAGES = 6
MIN_TERMS = 2


# Words a topic match should not turn on. Short enough to be a constant rather
# than a dependency; a coverage sweep does not need a stemmer.
_STOP = (
    "which what does do the a an and or of in on for to about state states stated "
    "obligation obligations document documents corpus silent address addresses "
    "requirement requirements is are any"
)
STOPWORDS = frozenset(_STOP.split())


def topic_terms(topic: str) -> set[str]:
    return {w.strip(".,;:?()'\"") for w in topic.lower().split()} - STOPWORDS - {""}


async def candidate_clauses(doc: dict, box: Toolbox, terms: set[str]) -> list[str]:
    """Which clauses of *this* document the branch should read, in ranked order.

    The global search is not enough on its own, and finding out why is the most
    useful thing the fan-out has produced. Asked which documents address
    politically exposed persons, a top-30 search over this corpus returned:

        PSN01A            8.1, 8.2, 8.4     -> branch said covered
        SFA 03AA-N01      8.1, 8.2          -> branch said covered
        Notice TCA-N03    8.1               -> branch said silent
        Notice 626        8.1               -> branch said silent

    Clause 8.1 is the *definition* of "close associate"; 8.2 is the obligation.
    Every one of those four documents contains both. Each branch judged its own
    evidence correctly, and the sweep was still wrong -- because on a corpus of
    eighteen near-identical AML notices (the entity-class near-duplication Day 4
    engineered on purpose, ADR-019), a global top-k gives different documents
    different amounts of evidence for the same reason a coin lands one way up.
    **A per-document verdict built on a global ranking reports "silent" when it
    means "this branch was shown less".**

    So the branch does its own retrieval inside its own document: the global hits
    it was given, plus any obligation in the document whose text matches the
    topic. That second source is what makes the branches symmetric.
    """
    paths = [h["section_path"] for h in doc.get("hits", [])]

    cursor, extra = None, []
    for _ in range(MAX_PAGES):
        args = {"doc_id": doc["doc_id"]} | ({"cursor": cursor} if cursor else {})
        raw = await box.tools["list_obligations"].ainvoke(args)
        if str(raw).startswith("TOOL ERROR"):
            break
        try:
            page = json.loads(raw)
        except (ValueError, TypeError):
            break
        for ob in page.get("obligations", []):
            blob = f"{ob.get('heading', '')} {ob.get('text', '')}".lower()
            hits = sum(1 for t in terms if t in blob)
            if hits >= MIN_TERMS:
                extra.append((hits, ob.get("section_path", "")))
        cursor = page.get("next_cursor")
        if not cursor:
            break

    for _, path in sorted(extra, key=lambda x: -x[0]):
        if path and path not in paths:
            paths.append(path)
    return paths[:BRANCH_CLAUSES]


async def clauses_of(topic: str, doc: dict, box: Toolbox) -> str:
    """The branch's evidence: its own document's topical clauses, read in full.

    Two earlier designs failed here, and both failed by answering a *different*
    question than the one asked.

    The first read the single top-ranked clause. For politically exposed persons
    that was clause 8.1 of four AML notices, which **defines** "close associate"
    rather than obliging anyone; the branch correctly found no obligation and
    therefore wrongly reported the document silent.

    The second read the document's whole obligation listing, compacted to 200
    characters per obligation. Compacting killed it: Notice 626's clause 8.2 reads
    *"A bank shall implement appropriate internal risk management systems,
    policies, procedures and controls to determine if a customer... is a
    politically exposed person"* -- and the phrase that matters falls past
    character 200. The branch was handed 24,000 characters of that document in
    which the topic appeared twice, and concluded it was silent.

    The lesson both share: for a coverage question, **truncation is not a smaller
    answer, it is a different and wrong one**.
    """
    parts = []
    for path in await candidate_clauses(doc, box, topic_terms(topic)):
        text = await box.tools["get_document_section"].ainvoke(
            {"doc_id": doc["doc_id"], "section_path": path, "max_chars": SECTION_CHARS}
        )
        if str(text).startswith("TOOL ERROR"):
            continue
        parts.append(f"clause {path}:\n{text}")
    return "\n\n".join(parts)[:BRANCH_CHARS]


async def inspect_one(topic: str, doc: dict, box: Toolbox) -> tuple[Finding | None, dict]:
    """One fan-out branch: one document, its matching clauses, one verdict.

    This is the only place in the graph where the subtasks are genuinely
    independent -- different documents, different context windows, no shared
    intermediate. If parallel fan-out is worth anything anywhere here, it is
    worth it here, which is why the fan-out measurement is taken on this node.

    It is also what makes the fan-out worth having beyond latency. Each branch
    holds several full clauses of one document; four of them together do not fit
    one context window, which is the prep plan's own *second* condition for
    multi-agent earning its keep. The first condition -- genuine parallelism --
    is measured in `fanout.py` and does not hold on this hardware.

    Async with the model call on `asyncio.to_thread`, because `chat` is blocking
    `httpx`: leaving it on the event loop would make a "parallel" fan-out run one
    branch at a time *in the orchestrator*, hiding the real bottleneck behind a
    self-inflicted one and reporting a speedup of 1.0 for the wrong reason.
    """
    text = await clauses_of(topic, doc, box) or doc.get("excerpt", "")

    reply = await asyncio.to_thread(
        chat,
        GAP_PROMPT.format(topic=topic, title=doc.get("title", ""), excerpt=text),
        model=box.model,
        schema=Finding.model_json_schema(),
        num_ctx=BRANCH_NUM_CTX,
    )
    try:
        return Finding.model_validate_json(reply.content), reply.spend()
    except Exception:  # noqa: BLE001
        return None, reply.spend()


# -- 5. citation checker -----------------------------------------------------


def check(answer: Answer | None, box: Toolbox) -> tuple[list[str], list[dict]]:
    """Layer 2, mechanically, with no model call. Day 6's `check_references`.

    Returns the violations and the citations that *did* resolve, so the
    synthesiser can be handed the good ones rather than the whole answer or
    nothing. A checker that can only reject is a gate; one that can strip is a
    filter, and a filter is what lets a partially-wrong answer still be useful.
    """
    if answer is None:
        return ["shape: the extractor returned nothing parseable"], []
    if box.ix is None:
        return [], [c.model_dump() for c in answer.citations]
    violations = check_references(box.ix, answer)
    good = [
        c.model_dump() for c in answer.citations if box.clause(c.doc_id, c.section_path) is not None
    ]
    return violations, good


# -- 6. synthesiser ----------------------------------------------------------

SYNTH_PROMPT = """Write the final answer to the request, using only the material below.

Every claim must be attributable to a clause listed under VERIFIED CITATIONS. Each is listed
as `document title, clause N`; refer to them in prose exactly that way and never by their
hexadecimal id. If the material does not answer the request, say so in one sentence and stop.

REQUEST
{question}

DRAFT ANSWER
{draft}

VERIFIED CITATIONS
{citations}

{extra}"""


def synthesise(question: str, draft: str, citations: list[dict], box: Toolbox, extra: str = ""):
    """The one node whose output a person reads, so it gets titles rather than ids.

    An earlier version listed citations as `doc_id:section_path` and told the
    model to write "<title>, clause <path>". It wrote the angle brackets --
    correctly, in the sense that nothing in its context said what the title was.
    A prompt that names a field the context does not contain is a prompt bug, and
    it looks exactly like a model failure in the output.
    """
    lines = []
    for c in citations:
        clause = box.clause(c["doc_id"], c["section_path"])
        title = (clause.title if clause else "") or c["doc_id"]
        lines.append(f"- {title}, clause {c['section_path']}")
    cites = "\n".join(lines) or "(none resolved against the index)"
    reply = chat(
        SYNTH_PROMPT.format(question=question, draft=draft, citations=cites, extra=extra),
        model=box.model,
    )
    return reply.content.strip(), reply.spend()
