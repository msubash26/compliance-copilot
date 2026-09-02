"""Writing the questions.

The generator's job is not to be clever. It is to produce a question a
compliance officer would actually say out loud, whose answer is in a clause we
already chose, and which does **not** give the answer away by quoting it.

That last point is the whole difficulty problem. Day 4's research measured BM25
at 92% recall@5 on naively generated questions, for a mechanical reason: a
question generated *from* a clause reuses that clause's rare vocabulary, so
lexical search cannot lose. So every prompt here carries explicit anti-leakage
rules -- and, because a prompt is a request rather than a guarantee, `verify`
checks them with a regex afterwards rather than trusting them.

One rule runs the other way. For a clause in a contested neighbourhood, the
question **must** name the entity class it binds. MAS publishes near-identical
AML/CFT notices for 25 classes of institution, so without that word the question
has no single right answer and the item would be unfair rather than hard. The
information needed to disambiguate belongs in the question; the difficulty is in
using it.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import subprocess
import time
from pathlib import Path

import httpx

from regops_evals.corpus import LEAK_PATTERNS, base_url
from regops_evals.schema import (
    Difficulty,
    GoldenItem,
    GoldSpan,
    Provenance,
    span_hash,
    write_jsonl,
)

NUM_PREDICT = 400
TIMEOUT_S = 180.0

SYSTEM = (
    "You write evaluation questions for a regulatory compliance retrieval system. "
    "You reply with one JSON object and nothing else."
)

# Rules every prompt inherits. Stated as prohibitions because that is what the
# mechanical checker can verify.
ANTI_LEAKAGE = """\
Rules, all of which matter:
- Never mention the notice or guideline number, the paragraph number, or the document title.
- Never quote a phrase of four or more words from the text.
- Ask it the way a compliance officer would say it out loud, not the way the text is written.
- Prefer ordinary professional wording over the text's own rare terms.
- The question must be answerable from the text shown, and must need it."""

ENTITY_RULE = """\
- The question MUST name the type of institution it is about ({entity}). Near-identical
  requirements exist for other kinds of institution, so without that word the question
  has no single right answer."""

JSON_RULE = """\
Reply with exactly this JSON and nothing else:
{"question": "...", "answer": "..."}
The answer is one or two sentences stating the requirement, in your own words."""

FACTUAL = """\
Here is a clause from a Singapore MAS regulatory document.

<clause>
{text}
</clause>

Write one question that this clause answers.
{anti}
{entity}

{json_rule}"""

MULTI_HOP = """\
Here are two clauses from two different Singapore MAS documents. The first cites the second.

<citing_clause source="{src_title}">
{src_text}
</citing_clause>

<cited_clause source="{tgt_title}">
{tgt_text}
</cited_clause>

Write one question that CANNOT be answered from either clause alone -- answering it needs
something from each. Do not phrase it as two questions joined by "and"; it should read as one
natural question whose answer happens to require both.
{anti}
{entity}

{json_rule}"""

COMPARATIVE = """\
Here is the same requirement as it appears in {n} different MAS notices, each binding a
different type of institution.

{blocks}

Write one question that compares these institution types on this requirement. Name EVERY one
of the {n} institution types shown, exactly as written above -- that is what makes the question
answerable, and a question naming only some of them has no single right answer. The answer must
state whether the requirement is the same or different for each, and say how.
{anti}

{json_rule}"""

TEMPORAL = """\
Here is a clause from a Singapore MAS regulatory document. It records something about *time* --
when a requirement took effect, which amendment changed it, or when it was deleted.

<clause>
{text}
</clause>
{extra}

Write one question about the timing: what took effect when, what changed it, or from what date
something applied. The answer must state the date or the instrument named in the clause.
{anti}
{entity}

{json_rule}"""

# Negatives get their own instruction per reason, because "ask something
# unanswerable" produces nonsense and nonsense measures nothing.
NEGATIVE_ANGLES = {
    "other_jurisdiction": (
        "Ask about the equivalent requirement imposed by a DIFFERENT regulator -- the Hong Kong "
        "Monetary Authority, the UK FCA, or Bank Negara Malaysia. The topic must be real and the "
        "question sensible; it is unanswerable only because this corpus holds Singapore MAS "
        "documents and nothing else."
    ),
    "out_of_scope_instrument": (
        "Ask about a requirement that lives in an Act or in subsidiary Regulations rather than in "
        "a MAS notice or guideline -- a statutory penalty, a section of an Act, a court remedy. "
        "The corpus holds notices and guidelines only."
    ),
    "withdrawn_requirement": (
        "Ask what a financial institution must do under this instrument TODAY, in a way that "
        "presumes it is still in force. It is not: it has been cancelled or withdrawn."
    ),
    "invented_specific": (
        "Ask about a specific numeric threshold, deadline, form number or percentage that sounds "
        "entirely plausible for this topic but that MAS has not in fact set. Do not signal that it "
        "is invented -- the question must read like any other."
    ),
    "unregulated_topic": (
        "Ask a sensible compliance-sounding question about something MAS does not regulate at all "
        "-- employment law, tax filing, data centre energy use, consumer product safety -- but "
        "phrase it as though it belonged in a financial regulator's remit."
    ),
}

NEGATIVE = """\
You are writing a question that a Singapore financial institution's compliance officer might
genuinely ask, but which CANNOT be answered from a corpus of MAS notices and guidelines.

For context, one real document in that corpus is titled: "{topic}"

{angle}

The question must sound completely ordinary -- a reviewer reading only the question should not
be able to tell it is unanswerable. Do not use words like "hypothetical" or "fictional".

Reply with exactly this JSON and nothing else:
{{"question": "...", "answer": "..."}}
The answer states, in one sentence, that this is not addressed in MAS notices or guidelines,
and why."""

WORD_RE = re.compile(r"[a-z]{4,}")
STOP = {
    "shall",
    "must",
    "with",
    "that",
    "this",
    "from",
    "such",
    "under",
    "which",
    "have",
    "been",
    "financial",
    "institution",
    "institutions",
    "their",
    "when",
    "where",
    "other",
    "sub",
    "paragraph",
    "including",
    "should",
    "would",
    "there",
    "these",
    "those",
    "into",
    "than",
    "also",
    "does",
    "each",
    "more",
    "made",
    "make",
    "will",
    "them",
    "they",
    "were",
    "what",
}


def leaks(query_type: str, question: str) -> list[str]:
    """Did the question name its own source? Negatives are exempt by design:
    naming a real instrument is what makes an unanswerable question plausible."""
    if query_type == "negative":
        return []
    return [name for name, rx in LEAK_PATTERNS if rx.search(question)]


def content_words(s: str) -> set[str]:
    return {w for w in WORD_RE.findall(s.lower()) if w not in STOP}


def vocab_overlap(question: str, span_text: str) -> float:
    """Jaccard over content words -- how much of the question is the clause's own vocabulary.

    Recorded on every item because it is the measurable form of the leakage
    problem. A high value is not automatically wrong (some terms are unavoidable:
    a question about beneficial ownership has to say "beneficial owner"), but the
    distribution is what tells you whether a set is testing retrieval or testing
    string matching.
    """
    q, s = content_words(question), content_words(span_text)
    if not q or not s:
        return 0.0
    return len(q & s) / len(q | s)


def _extract_json(raw: str) -> dict | None:
    """Pull the object out of whatever the model wrapped it in."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.S)
    start = raw.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(raw[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _prompt_for(cand: dict) -> str:
    qt = cand["query_type"]
    cls = cand["clauses"]
    entity = cand.get("entity")
    # The entity rule fires where it is needed: a contested neighbourhood, or a
    # comparative item (where it is the whole point).
    needs_entity = entity and (cand.get("near_dups", 0) >= 1 or qt in ("comparative", "multi_hop"))
    ent = ENTITY_RULE.format(entity=entity) if needs_entity else ""

    if qt == "factual_lookup":
        return FACTUAL.format(
            text=cls[0]["text"][:6000], anti=ANTI_LEAKAGE, entity=ent, json_rule=JSON_RULE
        )
    if qt == "multi_hop":
        return MULTI_HOP.format(
            src_title=cls[0]["doc_type"],
            src_text=cls[0]["text"][:4000],
            tgt_title=cls[1]["doc_type"],
            tgt_text=cls[1]["text"][:4000],
            anti=ANTI_LEAKAGE,
            entity=ent,
            json_rule=JSON_RULE,
        )
    if qt == "comparative":
        entities = cand["hint"]["entities"]
        blocks = "\n\n".join(
            f'<requirement institution="{entities[i]}">\n{c["text"][:2500]}\n</requirement>'
            for i, c in enumerate(cls)
        )
        return COMPARATIVE.format(n=len(cls), blocks=blocks, anti=ANTI_LEAKAGE, json_rule=JSON_RULE)
    if qt == "temporal":
        h = cand["hint"]
        extra = ""
        if h.get("kind") == "amendment":
            extra = f"\nThe clause records: {h['instrument']}, with effect from {h['effect_from']}."
        elif h.get("kind") == "deleted":
            extra = f"\nThe clause records a paragraph deleted by: {h['by']}."
        return TEMPORAL.format(
            text=cls[0]["text"][:6000],
            extra=extra,
            anti=ANTI_LEAKAGE,
            entity=ent,
            json_rule=JSON_RULE,
        )
    if qt == "negative":
        h = cand["hint"]
        return NEGATIVE.format(topic=h["topic_title"], angle=NEGATIVE_ANGLES[h["absence_reason"]])
    raise ValueError(f"unknown query_type {qt}")


async def _one(client: httpx.AsyncClient, model: str, prompt: str) -> tuple[dict | None, dict]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        # ADR-015's measurement: reasoning off is 15x faster, and writing a
        # question is not a reasoning-shaped task.
        "think": False,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.7, "num_predict": NUM_PREDICT},
    }
    r = await client.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    data = r.json()
    text = (data.get("message", {}).get("content") or "").strip()
    usage = {
        "prompt_tokens": data.get("prompt_eval_count"),
        "completion_tokens": data.get("eval_count"),
        "done_reason": data.get("done_reason"),
    }
    return _extract_json(text), usage


def _lf(sample: float):
    if sample <= 0:
        return None
    try:
        from langfuse import get_client

        c = get_client()
        return c if c.auth_check() else None
    except Exception:  # noqa: BLE001 - observability must never break a build
        return None


def _provenance(model: str, index: Path) -> Provenance:
    def _sh(cmd: list[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            return "unknown"

    manifest = Path("corpus/manifest.jsonl")
    manifest_sha = _sh(["sha256sum", str(manifest)]).split()[0] if manifest.exists() else "unknown"
    built = ""
    if index.exists():
        import datetime

        built = datetime.datetime.fromtimestamp(index.stat().st_mtime).isoformat(timespec="seconds")
    return Provenance(
        generator=model,
        corpus_manifest_sha=manifest_sha,
        index_built_at=built,
        parser=f"regops-ingest@{_sh(['git', 'rev-parse', '--short', 'HEAD']) or 'unknown'}",
    )


def generate_all(
    candidates: Path,
    out: Path,
    *,
    index: Path,
    model: str = "qwen3.5:9b",
    concurrency: int = 4,
    trace_sample: float = 0.1,
) -> int:
    payload = json.loads(candidates.read_text())
    flat: list[dict] = [c for cands in payload["candidates"].values() for c in cands]
    prov = _provenance(model, index)
    lf = _lf(trace_sample)
    rng = random.Random(0)
    started = time.time()

    job = None
    if lf is not None:
        job = lf.start_observation(
            name="golden-set-generation",
            as_type="span",
            input={"items": len(flat), "model": model},
            metadata={"day": "4", "task": "golden-set", "think": False},
        )

    results: dict[int, dict | None] = {}
    failures: list[tuple[int, str]] = []

    async def run_all() -> None:
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient() as client:

            async def run(i: int, cand: dict) -> None:
                async with sem:
                    t0 = time.time()
                    obj, usage = None, {}
                    # The model occasionally returns prose instead of the object
                    # it was asked for. Two retries costs seconds and is the
                    # difference between 148 items and the 150 the
                    # stratification declares.
                    for _attempt in range(3):
                        try:
                            obj, usage = await _one(client, model, _prompt_for(cand))
                        except (httpx.HTTPError, ValueError) as exc:
                            obj, usage = None, {"error": str(exc)[:160]}
                        # Anti-leakage is a prompt rule, and a prompt is a
                        # request rather than a guarantee. Checking it here,
                        # where a retry is still possible, is what makes it an
                        # enforced property instead of a recorded defect.
                        if (
                            obj
                            and obj.get("question")
                            and obj.get("answer")
                            and not leaks(cand["query_type"], str(obj["question"]))
                        ):
                            break
                        obj = None
                    results[i] = obj
                    if obj is None:
                        failures.append((i, str(usage.get("error", "unparseable JSON"))[:160]))
                    if lf is not None and (rng.random() < trace_sample or obj is None):
                        g = lf.start_observation(
                            name=f"golden-{cand['query_type']}",
                            as_type="generation",
                            model=model,
                            input=_prompt_for(cand)[:4000],
                            metadata={
                                "query_type": cand["query_type"],
                                "latency_s": round(time.time() - t0, 2),
                            },
                        )
                        g.update(
                            output=obj,
                            usage_details={
                                "input": usage.get("prompt_tokens") or 0,
                                "output": usage.get("completion_tokens") or 0,
                            },
                            level="ERROR" if obj is None else "DEFAULT",
                            status_message=usage.get("error"),
                        )
                        g.end()
                    if (len(results) % 25) == 0:
                        print(f"  {len(results)}/{len(flat)}", flush=True)

            await asyncio.gather(*(run(i, c) for i, c in enumerate(flat)))

    asyncio.run(run_all())

    items: list[GoldenItem] = []
    for i, cand in enumerate(flat):
        obj = results.get(i)
        if not obj or not obj.get("question") or not obj.get("answer"):
            # Already counted in `failures` by `run`; never dropped silently --
            # a set that quietly ships 148 items against a declared 150 is a set
            # whose stratification table is a lie.
            continue
        qt = cand["query_type"]
        spans = [
            GoldSpan(
                doc_id=c["doc_id"],
                section_path=c["section_path"],
                span_sha256=span_hash(c["text"]),
                why=(
                    "states the requirement"
                    if qt == "factual_lookup"
                    else f"one half of the {qt} pair"
                ),
            )
            for c in cand["clauses"]
        ]
        span_text = " ".join(c["text"] for c in cand["clauses"])
        question = str(obj["question"]).strip()
        try:
            items.append(
                GoldenItem(
                    id=f"gs-{len(items) + 1:04d}",
                    question=question,
                    answer=str(obj["answer"]).strip(),
                    query_type=qt,
                    gold_spans=spans,
                    entity_class=cand.get("entity"),
                    difficulty=Difficulty(
                        near_duplicates_at_0_10=cand.get("near_dups", 0),
                        vocab_overlap=round(vocab_overlap(question, span_text), 4)
                        if span_text
                        else 0.0,
                    ),
                    absence_reason=cand["hint"].get("absence_reason") if qt == "negative" else None,
                    provenance=prov,
                    notes=cand["hint"].get("hop_kind", "") or cand["hint"].get("kind", ""),
                )
            )
        except Exception as exc:  # noqa: BLE001 - a rejected item is a counted failure
            failures.append((i, f"schema: {str(exc)[:200]}"))

    write_jsonl(out, items)

    if job is not None:
        job.update(
            output={
                "generated": len(items),
                "requested": len(flat),
                "failed": len(failures),
                "wall_s": round(time.time() - started, 1),
            }
        )
        job.end()
        lf.flush()

    print(f"generated {len(items)}/{len(flat)} items -> {out}")
    if failures:
        print(f"{len(failures)} failed:")
        for i, why in failures[:10]:
            print(f"  [{i}] {flat[i]['query_type']}: {why}")
    return 0
