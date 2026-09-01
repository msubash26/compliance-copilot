"""Contextual retrieval: a one-sentence locator prepended to each chunk.

Two measurements decide the whole design of this module.

**Reasoning has to be off.** Timed on `qwen3.5:9b` over this corpus, a context
sentence costs 7.98 s with thinking on and 0.53 s with it off -- 17.9 hours
against 71 minutes over 8,055 chunks. Worse, the thinking tokens also exhausted
the 120-token cap, so the slow call returned a *truncated* answer. Writing a
locator is the least reasoning-shaped task there is. This is ADR-009 collecting.

**That forces the native API.** Day 0 established that `think: false` is not
honoured on Ollama's OpenAI-compatible endpoint -- neither `extra_body` nor
`reasoning_effort` reaches it. So this module talks to `/api/chat` directly and
traces to LangFuse by hand, rather than getting instrumentation for free from
`langfuse.openai`. The 15x saving is worth writing the span ourselves.

**The prompt carries an outline, not the document.** Anthropic's method situates
a chunk in its whole document; a 1,110-page notice cannot be situated that way,
and stuffing text in would invalidate the timing above. A clause's position in
MAS's numbering *is* its context, so the outline is title, type, effective date,
and the clause spine around the chunk -- small, bounded, and for legal text the
better signal.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass

import httpx

DEFAULT_MODEL = "qwen3.5:9b"
# Enough for one sentence. With thinking off, nothing else competes for it.
NUM_PREDICT = 120
DEFAULT_CONCURRENCY = 4
TIMEOUT_S = 120.0

SYSTEM = (
    "You situate an excerpt within a regulatory document. "
    "Reply with one short sentence and nothing else."
)

PROMPT = """\
{outline}

Here is the excerpt, from clause {section_path}:
<excerpt>
{chunk}
</excerpt>

Write one short sentence situating this excerpt within the document, so that it can
be found by search. Name the instrument, the clause number, and what the clause is
about. Do not quote the excerpt. Answer with the sentence only.\
"""


def base_url() -> str:
    """Ollama's native root. `OLLAMA_BASE_URL` points at the OpenAI-compatible /v1."""
    raw = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return raw.rstrip("/").removesuffix("/v1")


@dataclass(frozen=True)
class Outline:
    """The structural context a chunk gets instead of its document's text."""

    title: str
    doc_type: str
    issuer: str
    effective_date: str | None
    section_path: str
    heading: str | None
    spine: list[str]

    def render(self) -> str:
        lines = [
            f"Document: {self.title}",
            f"Issued by {self.issuer} as {self.doc_type}"
            + (f", effective {self.effective_date}" if self.effective_date else ""),
        ]
        if self.spine:
            lines.append("Clause outline: " + " | ".join(self.spine))
        here = f"This excerpt is from clause {self.section_path}"
        if self.heading:
            here += f" ({self.heading})"
        lines.append(here)
        return "\n".join(lines)


def spine_for(
    paths_and_headings: list[tuple[str, str | None]], path: str, width: int = 4
) -> list[str]:
    """The clause numbers either side of `path`, so the model can see where it sits."""
    labels = [f"{p} {h}".strip() if h else p for p, h in paths_and_headings]
    try:
        i = [p for p, _ in paths_and_headings].index(path)
    except ValueError:
        return labels[:width]
    lo = max(0, i - width // 2)
    return labels[lo : lo + width + 1]


async def _one(
    client: httpx.AsyncClient, model: str, outline: Outline, chunk: str
) -> tuple[str | None, dict]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": PROMPT.format(
                    outline=outline.render(),
                    section_path=outline.section_path,
                    chunk=chunk[:4000],
                ),
            },
        ],
        # The single line that turns 17.9 hours into 71 minutes. See ADR-015.
        "think": False,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": NUM_PREDICT},
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
    return (text or None), usage


def _client(sample: float):
    """A LangFuse client, or None when tracing is off or unconfigured.

    Never fatal: an ingest run that cannot reach the trace store still has to
    produce an index.
    """
    if sample <= 0:
        return None
    try:
        from langfuse import get_client

        client = get_client()
        return client if client.auth_check() else None
    except Exception:  # noqa: BLE001 - observability must not break ingestion
        return None


async def contextualise(
    items: list[tuple[str, Outline, str]],
    *,
    model: str = DEFAULT_MODEL,
    concurrency: int = DEFAULT_CONCURRENCY,
    on_done=None,
    trace_sample: float = 0.0,
) -> dict[str, str | None]:
    """Write a locator for each (key, outline, text). Failures map to None.

    A failed locator is not fatal: the chunk still embeds on its own text, which
    is exactly the control arm of Day 5's contextual on/off comparison.

    Tracing is **sampled**. 11,171 traced generations would drown the project and
    tell you nothing 20 of them would not, so `trace_sample` of them are recorded
    individually, every failure is recorded regardless, and the job as a whole
    gets one summary span carrying wall clock and token totals.
    """
    sem = asyncio.Semaphore(concurrency)
    out: dict[str, str | None] = {}
    lf = _client(trace_sample)
    rng = random.Random(0)  # sampling is reproducible, so a rerun traces the same items
    totals = {"n": 0, "failed": 0, "prompt": 0, "completion": 0}
    started = time.time()

    job = None
    if lf is not None:
        job = lf.start_observation(
            name="contextual-retrieval",
            as_type="span",
            input={"items": len(items), "model": model, "concurrency": concurrency},
            metadata={"day": "3", "task": "contextual-retrieval", "think": False},
        )

    async with httpx.AsyncClient() as client:

        async def run(key: str, outline: Outline, text: str) -> None:
            async with sem:
                sampled = lf is not None and rng.random() < trace_sample
                t0 = time.time()
                try:
                    ctx, usage = await _one(client, model, outline, text)
                except (httpx.HTTPError, ValueError) as exc:
                    ctx, usage = None, {"error": str(exc)[:120]}
                out[key] = ctx

                totals["n"] += 1
                totals["failed"] += ctx is None
                totals["prompt"] += usage.get("prompt_tokens") or 0
                totals["completion"] += usage.get("completion_tokens") or 0

                # Every failure is traced whether or not it was sampled.
                if lf is not None and (sampled or ctx is None):
                    gen = lf.start_observation(
                        name="locator",
                        as_type="generation",
                        model=model,
                        input=outline.render(),
                        metadata={"key": key, "latency_s": round(time.time() - t0, 3)},
                    )
                    gen.update(
                        output=ctx,
                        usage_details={
                            "input": usage.get("prompt_tokens") or 0,
                            "output": usage.get("completion_tokens") or 0,
                        },
                        level="ERROR" if ctx is None else "DEFAULT",
                        status_message=usage.get("error"),
                    )
                    gen.end()

                if on_done is not None:
                    on_done(key, ctx, usage)

        await asyncio.gather(*(run(*it) for it in items))

    if job is not None:
        wall = time.time() - started
        job.update(
            output={
                **totals,
                "wall_s": round(wall, 1),
                "s_per_item": round(wall / max(len(items), 1), 3),
            }
        )
        job.end()
        lf.flush()
    return out
