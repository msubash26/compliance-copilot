"""Three layers of validation, because Pydantic only checks the first one.

Day 6's research measured `qwen3.5:9b` answering 20 grounded questions over real
retrieved context with Ollama's `format: <json schema>` and a Pydantic model:

    schema-valid (Pydantic accepted it)                18 / 20
    every cited (doc_id, section_path) resolves        12 / 20

Six of the eighteen *validated* answers carried a citation to something that does
not exist. A representative one:

    {"doc_id": "[1]", "section_path": "clause 6.14 (d0000001:6.14)"}

The model filled the fields with the excerpt's *label* rather than the
identifiers sitting in the excerpt header. Pydantic is satisfied -- both fields
are strings, both are present -- and a compliance officer following the citation
is not. **"We use structured outputs" is not an answer to "how do you know the
citation is real".**

So validation here is three separate layers, each with its own measured rate:

    1. shape      Pydantic accepts the JSON.                    free
    2. reference  every (doc_id, section_path) is in the index. one lookup
    3. support    the cited clause contains the claim.          needs a judge

Only layers 1 and 2 can be repaired automatically, because only they have an
unambiguous violation to hand back. The repair loop retries once and **its own
success rate is measured** -- an unmeasured repair loop is just a slower way to
fail.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, ValidationError
from regops_retrieval.index import Index, base_url

MODEL = "qwen3.5:9b"
TIMEOUT_S = 300.0


class Citation(BaseModel):
    """One clause, addressed the way the corpus addresses it.

    `doc_id` and `section_path` rather than a free-text reference, because those
    two are what `get_document_section` takes and what the index can check. A
    citation that cannot be looked up is not a citation.
    """

    doc_id: str = Field(description="The 16-character document id, exactly as shown in the context")
    section_path: str = Field(description="The clause number, e.g. '6.14'")


class Answer(BaseModel):
    """The generator's contract.

    `sufficient` is an explicit field rather than a phrase to regex for, because
    abstention is a first-class outcome on this corpus -- 35 of the 150 golden
    items have no answer in it -- and Day 5's abstention machinery already reads
    a boolean.
    """

    answer: str = Field(description="The answer, or why the corpus does not contain one")
    citations: list[Citation] = Field(default_factory=list)
    sufficient: bool = Field(description="True if the context answers the question")


PROMPT = """Answer the question using only the numbered excerpts below.

Each excerpt's header is `[n] <title> · clause <path> (<doc_id>:<path>)`. When you cite,
`doc_id` is the 16-character hex string before the colon and `section_path` is what follows
it. Do not cite the excerpt number.

If the excerpts do not answer the question, set sufficient to false and say so.

QUESTION
{question}

EXCERPTS
{context}"""

REPAIR = """Your previous answer failed validation.

YOUR ANSWER
{prior}

WHAT IS WRONG
{violations}

The excerpts are unchanged and shown again below. Return corrected JSON in the same schema.
Cite only identifiers that appear in an excerpt header.

QUESTION
{question}

EXCERPTS
{context}"""


@dataclass
class Validated:
    """One attempt at a structured answer, and every layer's verdict."""

    item_id: str = ""
    shape_ok: bool = False
    reference_ok: bool = False
    # The first attempt's verdicts, kept separately. Reporting only the
    # post-repair rate would let a repair loop launder its own failures --
    # the interesting number is what the model produced unaided.
    shape_ok_first: bool = False
    reference_ok_first: bool = False
    answer: Answer | None = None
    violations: list[str] = field(default_factory=list)
    repaired: bool = False  # a second call was made and it fixed the failure
    repair_attempted: bool = False
    seconds: float = 0.0
    raw: str = ""
    # One record per model call. The first version of this reported the *first*
    # attempt's citations next to the *repair* attempt's violations, which reads
    # as a contradiction and is simply two different answers spliced together.
    attempts: list[dict] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.shape_ok and self.reference_ok


def _attempt(ans: Answer | None, problems: list[str]) -> dict:
    """One model call's verdict, self-contained."""
    return {
        "shape_ok": ans is not None,
        "reference_ok": ans is not None and not problems,
        "sufficient": ans.sufficient if ans else None,
        "citations": [c.model_dump() for c in ans.citations] if ans else [],
        "violations": problems,
    }


def _chat(model: str, prompt: str) -> tuple[str, float]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "format": Answer.model_json_schema(),
        "options": {"temperature": 0.0},
    }
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        body = r.json()
    except (httpx.HTTPError, ValueError):
        return "", time.perf_counter() - t0
    return (body.get("message", {}) or {}).get("content") or "", time.perf_counter() - t0


def check_shape(raw: str) -> tuple[Answer | None, list[str]]:
    """Layer 1. Free, and 18 of 20 pass it."""
    try:
        return Answer.model_validate_json(raw), []
    except ValidationError as exc:
        return None, [f"schema: {e['loc']}: {e['msg']}" for e in exc.errors()[:5]]
    except Exception as exc:  # noqa: BLE001 -- malformed JSON is a validation result
        return None, [f"schema: not JSON ({type(exc).__name__})"]


def check_references(ix: Index, answer: Answer) -> list[str]:
    """Layer 2. The one research 2 says is missing.

    An answer claiming to be grounded with no citation at all fails too: a
    citation-free claim is unfalsifiable, which is the property the whole
    pipeline exists to avoid. An abstention is exempt -- there is nothing to
    cite when the corpus does not answer.
    """
    if not answer.sufficient:
        return []
    if not answer.citations:
        return ["reference: answer claims to be sufficient but cites nothing"]
    bad = []
    for c in answer.citations:
        if ix.clause_by_uid(f"{c.doc_id}:{c.section_path}") is None:
            bad.append(
                f"reference: ({c.doc_id}, {c.section_path}) is not in the index — "
                "cite the doc_id and clause from an excerpt header"
            )
    return bad


def answer_once(
    ix: Index,
    question: str,
    context: str,
    *,
    model: str = MODEL,
    repair: bool = True,
    item_id: str = "",
) -> Validated:
    """Generate, validate all layers that need no judge, repair once if asked."""
    v = Validated(item_id=item_id)
    t0 = time.perf_counter()

    raw, _ = _chat(model, PROMPT.format(question=question, context=context))
    v.raw = raw
    ans, problems = check_shape(raw)
    v.shape_ok = v.shape_ok_first = ans is not None
    if ans is not None:
        problems = check_references(ix, ans)
        v.reference_ok = v.reference_ok_first = not problems
    v.answer, v.violations = ans, problems

    v.attempts.append(_attempt(ans, problems))

    if problems and repair:
        v.repair_attempted = True
        raw2, _ = _chat(
            model,
            REPAIR.format(
                prior=raw[:2000],
                violations="\n".join(problems),
                question=question,
                context=context,
            ),
        )
        ans2, problems2 = check_shape(raw2)
        if ans2 is not None:
            problems2 = check_references(ix, ans2)
        v.attempts.append(_attempt(ans2, problems2))
        if ans2 is not None and not problems2:
            v.answer, v.violations, v.raw = ans2, [], raw2
            v.shape_ok = v.reference_ok = v.repaired = True
        else:
            # Kept, not hidden: a repair that fails the same way twice is the
            # measurement that says the loop is not worth its latency. The
            # second attempt's answer is kept alongside its own violations so
            # the two are readable together.
            if ans2 is not None:
                v.answer = ans2
            v.violations = problems2 or problems

    v.seconds = time.perf_counter() - t0
    return v


def rates(rows: list[Validated]) -> dict:
    """The three layers as separate rates, plus what repair actually bought."""
    n = len(rows)
    if not n:
        return {}
    attempted = [r for r in rows if r.repair_attempted]
    return {
        "n": n,
        # unaided -- what the model produced before any repair
        "shape_ok_first": sum(r.shape_ok_first for r in rows),
        "reference_ok_first": sum(r.reference_ok_first for r in rows),
        "shape_rate_first": round(sum(r.shape_ok_first for r in rows) / n, 4),
        "reference_rate_first": round(sum(r.reference_ok_first for r in rows) / n, 4),
        # after one repair attempt
        "shape_ok": sum(r.shape_ok for r in rows),
        "reference_ok": sum(r.reference_ok for r in rows),
        "valid": sum(r.valid for r in rows),
        "shape_rate": round(sum(r.shape_ok for r in rows) / n, 4),
        "reference_rate": round(sum(r.reference_ok for r in rows) / n, 4),
        "repair_attempted": len(attempted),
        "repaired": sum(r.repaired for r in rows),
        "repair_rate": round(sum(r.repaired for r in rows) / len(attempted), 4)
        if attempted
        else None,
        "abstained": sum(1 for r in rows if r.answer and not r.answer.sufficient),
        # Two very different failures, both caught by layer 2 and worth separating:
        # citing something that does not exist, and citing nothing at all.
        "cited_nothing": sum(1 for r in rows if any("cites nothing" in v for v in r.violations)),
        "cited_unresolvable": sum(
            1 for r in rows if any("not in the index" in v for v in r.violations)
        ),
        "repair_changed_nothing": sum(
            1
            for r in rows
            if len(r.attempts) == 2 and r.attempts[0]["citations"] == r.attempts[1]["citations"]
        ),
        "p50_s": round(sorted(r.seconds for r in rows)[n // 2], 3),
    }


def write(rows: list[Validated], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "model": MODEL,
                "summary": rates(rows),
                "rows": [
                    {
                        "item_id": r.item_id,
                        "shape_ok_first": r.shape_ok_first,
                        "reference_ok_first": r.reference_ok_first,
                        "shape_ok": r.shape_ok,
                        "reference_ok": r.reference_ok,
                        "repaired": r.repaired,
                        "repair_attempted": r.repair_attempted,
                        "violations": r.violations,
                        "sufficient": r.answer.sufficient if r.answer else None,
                        "citations": [c.model_dump() for c in r.answer.citations]
                        if r.answer
                        else [],
                        "attempts": r.attempts,
                        "seconds": round(r.seconds, 3),
                    }
                    for r in rows
                ],
            },
            indent=2,
        )
        + "\n"
    )
