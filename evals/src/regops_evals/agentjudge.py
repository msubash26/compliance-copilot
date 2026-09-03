"""Layer 3, finally: is the prose supported by the clauses it cited?

Deferred twice for reasons that were good both times. On Day 6 there was no
judge. On Day 7 layer 2 -- the mechanical check that every cited identifier
resolves against the index -- was already at its ceiling on the coverage set (0
unresolvable of 12) so a judge would have been measuring a rate with no room to
move. Day 8's thirty tasks are the first thing in this project a judge has
something to disagree with, and research 3 measured that it does: over eight of
the supervisor's own answers it refused two.

**Three axes, scored separately, because they fail for different reasons.**

- `supported` -- every claim in the answer appears in the cited clauses. This is
  groundedness, and it is the axis a fabricated threshold fails.
- `complete` -- the answer covers what the gold spans actually state. An answer
  can be perfectly supported and answer a third of the question; a composite
  score hides exactly that.
- `cited_correctly` -- the citations are the clauses the support came from. Layer
  2 proves an identifier *resolves*; only a reader can tell whether it is the
  right clause. This is the axis that catches a real citation attached to the
  wrong sentence, which is the failure a compliance reviewer would care about
  most and the only one no mechanical check can see.

**The judge is `qwen3.8`, not `qwen3.5:9b`.** ADR-017's rule: the checker is not
the writer, because a model agreeing with itself is not evidence. Research 3
measured 3.6s per call, so thirty tasks is about two minutes -- an order of
magnitude cheaper than Day 5's timings implied, and cheap enough that the judge
runs on every arm rather than a sample.

**What it is given, and what it is not.** The judge sees the clauses the answer
cited, resolved out of the index here, and the gold answer. It does not see which
architecture produced the answer, how long it took, or what any mechanical check
concluded -- an arm label in the prompt is an invitation to score the label.

**And it never gates.** The judge's verdicts are reported in their own columns.
Research 3's caveat is the reason: 8 of 8 on a *blatant* poison (an invented
17-year retention period) says nothing about a subtle one, and a build that fails
on an uncalibrated model's opinion fails for reasons nobody can audit. Gating is
the mechanical metrics' job; `golden/judge_calibration/` is what would let this
one earn more.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field

import httpx
from regops_retrieval.index import Index, base_url

JUDGE_MODEL = "qwen3.8:latest"
TIMEOUT_S = 300.0

AXES = ("supported", "complete", "cited_correctly")

JUDGE_SYSTEM = (
    "You grade an assistant's answer against the regulatory clauses it cited. "
    "You are strict, you never use knowledge of regulation that is not in the "
    "clauses shown, and you reply with JSON only."
)

JUDGE_PROMPT = """QUESTION
{question}

CLAUSES THE ASSISTANT CITED
{clauses}

REFERENCE ANSWER (written from the clauses that actually answer this question)
{gold}

THE ASSISTANT'S ANSWER
{answer}

Grade three separate things. Do not let one verdict decide another.

1. supported: is EVERY factual claim in the assistant's answer stated in the clauses
   above? A claim that adds a threshold, a deadline, a period or a requirement the
   clauses do not state is NOT supported, even if it happens to be true in reality.
   An answer that cites no clause at all cannot be supported.
2. complete: does the assistant's answer cover what the reference answer states? An
   answer that is correct as far as it goes but omits half of the requirement is not
   complete.
3. cited_correctly: are the clauses listed above the ones the answer's support
   actually comes from? A clause that is real, and about a different subject than the
   claim it is attached to, fails this.

Also say whether the assistant in effect refused to answer -- said the corpus does
not address the question, or that it could not find the answer -- regardless of
what else it wrote.

Reply with exactly this JSON and nothing else:
{{"supported": true/false, "complete": true/false, "cited_correctly": true/false,
  "refused": true/false, "why": "one short sentence"}}"""

# Enough of a clause to judge against, and no more: the judge's context is
# 40,960 on this box and six clauses at 3,000 characters is comfortable inside it.
CLAUSE_CHARS = 3000
MAX_CLAUSES = 8


@dataclass
class Verdict:
    task_id: str
    arm: str
    supported: bool = False
    complete: bool = False
    cited_correctly: bool = False
    refused: bool = False
    why: str = ""
    error: str = ""
    seconds: float = 0.0

    def axes(self) -> dict[str, bool]:
        return {a: bool(getattr(self, a)) for a in AXES}


def _extract_json(raw: str) -> dict | None:
    raw = (raw or "").strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def clause_text(ix: Index, uids: list[str]) -> str:
    """The cited clauses, resolved. Unresolvable ones are shown as such.

    Deliberately not filtered. An answer whose only citation does not exist has
    to be judgeable as *unsupported*, and silently dropping the bad reference
    would hand it an empty evidence list that reads the same as a shy answer.
    """
    parts = []
    for uid in uids[:MAX_CLAUSES]:
        clause = ix.clause_by_uid(uid)
        if clause is None:
            parts.append(f"[{uid}] -- NOT FOUND IN THE INDEX")
            continue
        parts.append(
            f"[{uid}] {clause.title or ''} · clause {clause.section_path}\n"
            f"{(clause.text or '')[:CLAUSE_CHARS]}"
        )
    return "\n\n".join(parts) or "(the assistant cited no clause)"


async def _one(client: httpx.AsyncClient, model: str, prompt: str) -> tuple[dict | None, float]:
    t0 = time.perf_counter()
    try:
        r = await client.post(
            f"{base_url()}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "think": False,
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        body = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}, time.perf_counter() - t0
    content = (body.get("message", {}) or {}).get("content") or ""
    return _extract_json(content), time.perf_counter() - t0


async def judge_rows(
    rows: list[dict],
    index,
    *,
    model: str = JUDGE_MODEL,
    concurrency: int = 2,
) -> list[Verdict]:
    """Judge every answered row. Abstentions and negatives are skipped, not scored.

    An abstention has no claims to support and a negative has no reference answer
    to be complete against; judging them anyway spends a fifth of the pass
    measuring nothing and then reports the nothing as a rate. They are counted by
    the mechanical abstention metrics instead, which is where that question
    belongs.
    """
    ix = Index(index) if not isinstance(index, Index) else index
    close = not isinstance(index, Index)
    try:
        work = [r for r in rows if not r["must_abstain"] and not r["abstained"]]
        out: list[Verdict] = []
        sem = asyncio.Semaphore(concurrency)

        async def run(client, r: dict) -> None:
            prompt = JUDGE_PROMPT.format(
                question=r["question"],
                clauses=clause_text(ix, r["cited_uids"]),
                gold=r.get("gold_answer") or "(none)",
                answer=r["answer"][:6000],
            )
            async with sem:
                obj, secs = await _one(client, model, prompt)
            v = Verdict(task_id=r["task_id"], arm=r["arm"], seconds=round(secs, 2))
            if obj is None:
                v.error = "unparseable judge reply"
            elif "__error__" in obj:
                v.error = str(obj["__error__"])[:200]
            else:
                v.supported = bool(obj.get("supported"))
                v.complete = bool(obj.get("complete"))
                v.cited_correctly = bool(obj.get("cited_correctly"))
                v.refused = bool(obj.get("refused"))
                v.why = str(obj.get("why", ""))[:300]
            out.append(v)

        async with httpx.AsyncClient() as client:
            await asyncio.gather(*(run(client, r) for r in work))
        return sorted(out, key=lambda v: (v.arm, v.task_id))
    finally:
        if close:
            ix.close()


def summarise(verdicts: list[Verdict]) -> dict:
    """Per axis: how many passed, out of how many were judged.

    Counts beside rates, for Day 6 Phase 1's reason -- over thirty tasks a rate
    alone turns one item into 3.3 points and reads as a trend.
    """
    ok = [v for v in verdicts if not v.error]
    n = len(ok)

    def rate(axis: str) -> dict:
        passed = sum(1 for v in ok if getattr(v, axis))
        return {"passed": passed, "n": n, "rate": round(passed / n, 4) if n else None}

    return {
        "model": JUDGE_MODEL,
        "judged": n,
        "errors": len(verdicts) - n,
        "seconds_total": round(sum(v.seconds for v in verdicts), 1),
        "seconds_per_call": round(sum(v.seconds for v in verdicts) / len(verdicts), 2)
        if verdicts
        else None,
        "axes": {a: rate(a) for a in AXES},
        # Passing all three is the interesting composite, and it is reported
        # rather than gated. See the module docstring.
        "all_three": {
            "passed": sum(1 for v in ok if all(v.axes().values())),
            "n": n,
            "rate": round(sum(1 for v in ok if all(v.axes().values())) / n, 4) if n else None,
        },
        "judge_says_refused": sum(1 for v in ok if v.refused),
    }


@dataclass
class Calibration:
    """One hand-scored item, and what the judge said about the same one.

    Kept as its own artifact under `golden/judge_calibration/`. It is never
    merged into `golden/v1` and never used to relabel an item: ADR-017 draws the
    line at `human_reviewed: false` on every golden item, and an agreement study
    that quietly promotes twenty of them dissolves the boundary it was measuring
    against.
    """

    task_id: str
    arm: str
    human: dict[str, bool] = field(default_factory=dict)
    judge: dict[str, bool] = field(default_factory=dict)


def agreement(pairs: list[Calibration]) -> dict:
    """Per-axis agreement, plus the direction of every disagreement.

    A single accuracy number over three axes hides which axis is broken and in
    which direction. "The judge is harsh on completeness and lenient on
    citations" is an actionable sentence; "83% agreement" is not.
    """
    out: dict = {"n": len(pairs), "axes": {}}
    for axis in AXES:
        both = [p for p in pairs if axis in p.human and axis in p.judge]
        agree = sum(1 for p in both if p.human[axis] == p.judge[axis])
        harsh = sum(1 for p in both if p.human[axis] and not p.judge[axis])
        lenient = sum(1 for p in both if not p.human[axis] and p.judge[axis])
        out["axes"][axis] = {
            "n": len(both),
            "agree": agree,
            "rate": round(agree / len(both), 4) if both else None,
            "judge_harsher": harsh,
            "judge_more_lenient": lenient,
        }
    return out
