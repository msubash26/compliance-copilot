"""Checking the set, with something other than the thing that wrote it.

Two independent layers, deliberately separated because they fail differently and
because only one of them can run in CI.

**Mechanical checks** are cheap, decisive and need no GPU: does the gold span
still resolve, does its hash still match, did the question leak its source, is
the answer actually grounded in the span. These also serve as the anti-rot check
-- Day 3 moved this corpus from 8,055 clauses to 11,171, so a set that pins
`section_path` is pinned to a parser, and `resolved / moved / missing` is how
that shows up as a failing check rather than a slow decay in the numbers.

**The judge** is a second model. `qwen3.8` verifies what `qwen3.5:9b` wrote,
because a model agreeing with itself is not evidence of anything. It answers two
questions per item -- can this be answered from this span, and can it be answered
*without* it -- and for negatives it does the harder inverse: we search the
corpus hard, top-20 on both arms, and ask whether anything found actually answers
the question. A negative that turns out to be answerable is the most damaging
item in the set, because it teaches the eval to reward abstention when abstention
is wrong.

Disagreement is a flag, never a deletion. Removing items a checker disliked would
tune the set toward whatever the checker is good at, which is the same failure as
removing items a baseline retrieved.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from regops_evals.corpus import Index, base_url, embed_one
from regops_evals.generate import content_words, leaks
from regops_evals.schema import GoldenItem, Verification, read_jsonl, span_hash, write_jsonl

TIMEOUT_S = 180.0


# Below this, an answer's vocabulary barely appears in the span it is supposed to
# come from -- usually a sign the model answered from its own knowledge.
MIN_ANSWER_GROUNDING = 0.25

# How much of a candidate clause the negative-set judge is shown. This was 700
# characters, and 700 characters is where the negative set's one known defect
# came from: Notice 653 is a 12,689-character clause whose disclosure-template
# requirement begins at character 3,697, so the judge was asked whether the
# corpus answers a question about disclosure templates while being shown a
# window that stopped 3,000 characters short of the answer. It said no, with
# confidence 1.0. Raised, and what is still cut is now labelled. See ADR-024.
NEGATIVE_EXCERPT_CHARS = 6000

JUDGE_ANSWERABLE = """\
<excerpt>
{span}
</excerpt>

Question: {question}

Can this question be answered using ONLY the excerpt above? Then, if it can, does the
following proposed answer agree with the excerpt?

Proposed answer: {answer}

Reply with exactly this JSON and nothing else:
{{"answerable": true/false, "agrees": true/false, "why": "one short sentence"}}"""

JUDGE_CLOSED_BOOK = """\
Question: {question}

Answer this question about Singapore MAS regulation from your own knowledge, with no documents
provided. Be specific: state the actual requirement, not the kind of thing it might be. If you
do not know the specific requirement, say so plainly.

Reply with exactly this JSON and nothing else:
{{"knows": true/false, "answer": "one sentence, or an admission that you do not know"}}"""

# A model claiming to know is not evidence that it does. Measured on this set:
# asked closed-book, `qwen3.8` answered `knows: true` for 45 of 115 grounded
# items, but its answers were generic regulatory boilerplate that did not match
# the gold answer -- "cybersecurity, data privacy and operational resilience"
# where the clause says money-laundering risk. So the self-report is discarded
# and the closed-book answer is compared with the gold answer instead. An item
# is only "answerable without the corpus" when the model, unaided, produces
# substantially what the clause says.
CLOSED_BOOK_MATCH = 0.45

JUDGE_NEGATIVE = """\
A search over a corpus of Singapore MAS notices and guidelines returned these excerpts for the
question below. Decide whether ANY of them actually answers it.

Question: {question}

{excerpts}

An excerpt "answers" the question only if it states the specific thing asked for. Being about
the same general topic is not answering.

Reply with exactly this JSON and nothing else:
{{"answered": true/false, "which": "the excerpt number, or none", "why": "one short sentence"}}"""


@dataclass
class Checks:
    """The per-item outcome, before it is folded into a confidence."""

    drift: str = "resolved"  # resolved | moved | missing
    leaks: list[str] = field(default_factory=list)
    answer_grounding: float = 1.0
    entity_named: bool = True
    judge_answerable: bool | None = None
    judge_agrees: bool | None = None
    judge_closed_book_known: bool | None = None
    closed_book_overlap: float = 0.0
    closed_book_answer: str = ""
    negative_answered: bool | None = None
    judge_why: str = ""


def check_spans(item: GoldenItem, ix: Index) -> tuple[str, list[str]]:
    """Re-bind every gold span against a live index.

    Three outcomes, and the middle one is the point: `moved` means the clause is
    still there under that path but its text is not what the question was written
    from. That is a parser change, and it is invisible to any check that only
    asks whether the path exists.
    """
    if not item.gold_spans:
        return "resolved", []
    states, notes = [], []
    for sp in item.gold_spans:
        cl = ix.clause(sp.doc_id, sp.section_path)
        if cl is None:
            states.append("missing")
            notes.append(f"{sp.doc_id}:{sp.section_path} not in index")
        elif span_hash(cl.text) != sp.span_sha256:
            states.append("moved")
            notes.append(f"{sp.doc_id}:{sp.section_path} text changed since generation")
        else:
            states.append("resolved")
    for worst in ("missing", "moved"):
        if worst in states:
            return worst, notes
    return "resolved", notes


def check_leakage(item: GoldenItem) -> list[str]:
    """Did the question name its own source?

    Generation already retries on a leak, so this is the independent confirmation
    rather than the first line of defence -- and it still has to run, because the
    rule that matters is the one checked on the artifact that shipped.
    """
    return leaks(item.query_type, item.question)


def check_answer_grounding(item: GoldenItem, ix: Index) -> float:
    """Fraction of the answer's content words that appear in the gold spans."""
    if not item.gold_spans:
        return 1.0
    span_text = " ".join(
        (c.text if (c := ix.clause(sp.doc_id, sp.section_path)) else "") for sp in item.gold_spans
    )
    a, s = content_words(item.answer), content_words(span_text)
    return len(a & s) / len(a) if a else 0.0


def check_entity_named(item: GoldenItem) -> bool:
    """A contested item must name the entity class, or it has no single right answer.

    Matched on the head noun rather than the full title phrase: MAS writes
    "Credit Card or Charge Card Licensees" and a compliance officer says
    "credit card licensees".
    """
    contested = item.difficulty and item.difficulty.near_duplicates_at_0_10 >= 1
    if item.query_type == "comparative":
        contested = True
    if not contested or not item.entity_class:
        return True
    q = item.question.lower()
    words = [w for w in re.findall(r"[a-z]{4,}", item.entity_class.lower())]
    # MAS titles a class in the plural ("Banks"); a question asks in the singular
    # ("a bank"). Match on the stem so that is not read as a missing entity.
    return any(w.rstrip("s") in q for w in words) if words else True


async def _ask(client: httpx.AsyncClient, model: str, prompt: str) -> dict | None:
    from regops_evals.generate import _extract_json

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 250},
    }
    try:
        r = await client.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        return _extract_json(r.json().get("message", {}).get("content") or "")
    except (httpx.HTTPError, ValueError):
        return None


def _confidence(c: Checks, item: GoldenItem) -> float:
    """A blunt, legible score. Its only job is to rank the review queue.

    Deliberately not calibrated -- calling it a probability would be a claim the
    evidence does not support. It is an ordering over "how much does this item
    want a human to look at it".
    """
    score = 1.0
    if c.drift == "missing":
        score -= 0.6
    elif c.drift == "moved":
        score -= 0.35
    score -= 0.15 * len(c.leaks)
    if not c.entity_named:
        score -= 0.2
    if c.answer_grounding < MIN_ANSWER_GROUNDING:
        score -= 0.2
    if item.query_type == "negative":
        if c.negative_answered is True:
            score -= 0.6  # the most damaging failure in the set
        elif c.negative_answered is None:
            score -= 0.1
    else:
        if c.judge_answerable is False:
            score -= 0.4
        if c.judge_agrees is False:
            score -= 0.25
        # Answerable without the corpus means the item measures the model, not
        # the retriever. A real finding, but a weaker one than the others.
        if c.judge_closed_book_known is True:
            score -= 0.15
        if c.judge_answerable is None:
            score -= 0.1
    return max(0.0, min(1.0, round(score, 3)))


def _status(c: Checks, item: GoldenItem) -> tuple[str, list[str]]:
    fails = []
    if c.drift != "resolved":
        fails.append(f"span_{c.drift}")
    fails += [f"leak_{name}" for name in c.leaks]
    if not c.entity_named:
        fails.append("entity_not_named")
    if c.answer_grounding < MIN_ANSWER_GROUNDING:
        fails.append(f"answer_grounding_{c.answer_grounding:.2f}")
    if item.query_type == "negative":
        if c.negative_answered is True:
            fails.append("negative_is_answerable")
    else:
        if c.judge_answerable is False:
            fails.append("judge_says_not_answerable_from_span")
        if c.judge_agrees is False:
            fails.append("judge_disagrees_with_answer")
        if c.judge_closed_book_known is True:
            fails.append("answerable_without_corpus")
    return ("flagged" if fails else "machine_verified"), fails


def negative_excerpts(items: list[GoldenItem], ix: Index) -> dict[str, str]:
    """Search the corpus hard for every negative, before the judge is loaded.

    Ollama serialises against one loaded model, so interleaving embedding calls
    with judge calls would swap a 17.7 GB model in and out 35 times. Every
    embedding this pass needs is therefore done here, in one batch, while
    `nomic-embed-text` is the resident model -- the same batch-by-model rule the
    Day 3 pipeline runs under.
    """
    out: dict[str, str] = {}
    for it in items:
        if it.query_type != "negative":
            continue
        vec = embed_one(it.question)
        uids = [u for u, _ in ix.search_bm25(it.question, 10)]
        uids += [u for u, _ in ix.search_dense(it.question, 10, vec=vec)]
        seen, ex = set(), []
        for u in uids:
            if u in seen:
                continue
            seen.add(u)
            doc_id, _, path = u.partition(":")
            if cl := ix.clause(doc_id, path):
                body = " ".join(cl.text.split())
                if len(body) > NEGATIVE_EXCERPT_CHARS:
                    # Say so. A judge told "this excerpt is complete" when it is
                    # not will answer "no, the corpus does not say that" with
                    # perfect confidence -- which is exactly what happened to
                    # gs-0118. See ADR-024.
                    body = (
                        body[:NEGATIVE_EXCERPT_CHARS]
                        + f" […truncated from {len(body):,} characters]"
                    )
                ex.append(f"[{len(ex) + 1}] {body}")
            if len(ex) >= 12:
                break
        out[it.id] = "\n\n".join(ex)
    return out


async def _judge_all(
    items: list[GoldenItem],
    checks: dict[str, Checks],
    ix: Index,
    model: str,
    excerpts: dict[str, str],
    concurrency: int = 3,
) -> None:
    sem = asyncio.Semaphore(concurrency)
    done = [0]

    async def one(client: httpx.AsyncClient, item: GoldenItem) -> None:
        async with sem:
            c = checks[item.id]
            if item.query_type == "negative":
                obj = await _ask(
                    client,
                    model,
                    JUDGE_NEGATIVE.format(
                        question=item.question, excerpts=excerpts.get(item.id, "")
                    ),
                )
                if obj is not None:
                    c.negative_answered = bool(obj.get("answered"))
                    c.judge_why = str(obj.get("why", ""))[:200]
            else:
                span = "\n\n".join(
                    cl.text[:3000]
                    for sp in item.gold_spans
                    if (cl := ix.clause(sp.doc_id, sp.section_path))
                )
                obj = await _ask(
                    client,
                    model,
                    JUDGE_ANSWERABLE.format(span=span, question=item.question, answer=item.answer),
                )
                if obj is not None:
                    c.judge_answerable = bool(obj.get("answerable"))
                    c.judge_agrees = bool(obj.get("agrees"))
                    c.judge_why = str(obj.get("why", ""))[:200]
                cb = await _ask(client, model, JUDGE_CLOSED_BOOK.format(question=item.question))
                if cb is not None:
                    cb_answer = str(cb.get("answer", ""))
                    a, g = content_words(cb_answer), content_words(item.answer)
                    c.closed_book_overlap = round(len(a & g) / len(a | g), 3) if (a or g) else 0.0
                    c.closed_book_answer = cb_answer[:400]
                    c.judge_closed_book_known = (
                        bool(cb.get("knows")) and c.closed_book_overlap >= CLOSED_BOOK_MATCH
                    )
            done[0] += 1
            if done[0] % 25 == 0:
                print(f"  judged {done[0]}/{len(items)}", flush=True)

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(client, it) for it in items))


def write_review_queue(path: Path, items: list[GoldenItem], checks: dict[str, Checks], ix: Index):
    """Lowest confidence first, gold span inline.

    This is the artifact the prep plan's three hours of human review should be
    spent on. Spreading that attention evenly over 150 items would mostly
    re-read items that are fine; this puts the contested ones at the top and
    quotes the clause so a person can adjudicate without opening the PDF.
    """
    ordered = sorted(items, key=lambda i: (i.verification.confidence, i.id))
    out = [
        "# Golden set v1 — human review queue",
        "",
        "Ascending confidence: the items most likely to be wrong are first. Confidence is a",
        "ranking device, not a calibrated probability — see ADR-017.",
        "",
        f"{sum(1 for i in items if i.verification.status == 'flagged')} of {len(items)} items"
        " carry at least one failed check.",
        "",
    ]
    for it in ordered:
        v = it.verification
        c = checks[it.id]
        out += [
            f"## {it.id} · {it.query_type} · confidence {v.confidence}",
            "",
            f"**Q.** {it.question}",
            "",
            f"**A.** {it.answer}",
            "",
        ]
        if v.failures:
            out += [f"**Failed checks:** {', '.join(v.failures)}", ""]
        if c.judge_why:
            out += [f"**Verifier ({v.verifier}):** {c.judge_why}", ""]
        if c.closed_book_answer:
            out += [
                f"**Verifier answering with no documents** (overlap with gold "
                f"{c.closed_book_overlap}): {c.closed_book_answer}",
                "",
            ]
        if it.absence_reason:
            out += [f"**Claimed unanswerable because:** `{it.absence_reason}`", ""]
        for sp in it.gold_spans:
            cl = ix.clause(sp.doc_id, sp.section_path)
            head = f"{cl.title} · clause {sp.section_path}" if cl else f"{sp.section_uid} (MISSING)"
            body = " ".join(cl.text.split())[:900] if cl else "—"
            out += [f"**Gold span** — {head}", "", f"> {body}", ""]
        out += ["---", ""]
    # Rstrip each line: the quoted clause text and the verifier's sentences carry
    # trailing spaces, and this file is regenerated on every verify run -- left
    # alone it would be rewritten by the whitespace hook every single time.
    path.write_text("\n".join(line.rstrip() for line in out) + "\n")


def run_verify(
    golden: Path,
    index: Path,
    *,
    model: str = "qwen3.8:latest",
    judge: bool = True,
    queue: Path | None = None,
    report: Path | None = None,
) -> int:
    items = read_jsonl(golden)
    ix = Index(index)
    checks: dict[str, Checks] = {}
    started = time.time()

    for it in items:
        drift, _ = check_spans(it, ix)
        checks[it.id] = Checks(
            drift=drift,
            leaks=check_leakage(it),
            answer_grounding=round(check_answer_grounding(it, ix), 3),
            entity_named=check_entity_named(it),
        )

    excerpts: dict[str, str] = {}
    if judge:
        n_neg = sum(1 for i in items if i.query_type == "negative")
        print(f"searching the corpus for {n_neg} negatives (embedder resident)")
        excerpts = negative_excerpts(items, ix)
        print(f"judging {len(items)} items with {model} (a different model from the generator)")
        asyncio.run(_judge_all(items, checks, ix, model, excerpts))

    for it in items:
        c = checks[it.id]
        prior = it.verification
        status, fails = _status(c, it)
        if not judge:
            # `--no-judge` is the CI and pre-flight path: it re-runs the
            # mechanical checks and must not silently discard a judged run's
            # findings. Day 5's Phase 0 check did exactly that -- it reset 28
            # flagged items to unverified -- which is a data loss a benchmark
            # would then read as a cleaner instrument than it has.
            it.verification = prior.model_copy(
                update={
                    "span_exists": c.drift != "missing",
                    "no_leakage": not c.leaks,
                    # A newly failing mechanical check still flags the item; a
                    # previously judged flag is never cleared by a run that did
                    # not re-ask the judge.
                    "status": "flagged" if (fails or prior.status == "flagged") else prior.status,
                    "failures": sorted(set(prior.failures) | set(fails)),
                }
            )
            continue
        it.verification = Verification(
            span_exists=c.drift != "missing",
            answerable_from_span=c.judge_answerable,
            no_leakage=not c.leaks,
            not_answerable_without_span=(
                None if c.judge_closed_book_known is None else not c.judge_closed_book_known
            ),
            verifier=model,
            status=status,
            human_reviewed=False,
            confidence=_confidence(c, it),
            failures=fails,
        )

    write_jsonl(golden, items)

    # The counts. "The verifier disagreed on 14 of 150" is a more honest quality
    # claim than a clean file, so this is printed and persisted, not swallowed.
    tally: dict[str, int] = {}
    for it in items:
        for f in it.verification.failures:
            tally[f.split("_0.")[0]] = tally.get(f.split("_0.")[0], 0) + 1
    flagged = [i for i in items if i.verification.status == "flagged"]
    summary = {
        "items": len(items),
        "flagged": len(flagged),
        "machine_verified": len(items) - len(flagged),
        "human_reviewed": 0,
        "verifier": model if judge else None,
        "drift": {
            k: sum(1 for c in checks.values() if c.drift == k)
            for k in ("resolved", "moved", "missing")
        },
        "failures_by_check": dict(sorted(tally.items(), key=lambda kv: -kv[1])),
        "wall_s": round(time.time() - started, 1),
    }
    print(json.dumps(summary, indent=2))

    if queue:
        write_review_queue(queue, items, checks, ix)
        print(f"review queue -> {queue}")
    if report:
        report.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"report -> {report}")

    # Drift is the only fatal outcome: it means the set no longer describes the
    # index. Flags are information for a human, not a build failure.
    if summary["drift"]["missing"] or summary["drift"]["moved"]:
        print("FAIL: gold spans no longer bind to this index")
        return 1
    return 0
