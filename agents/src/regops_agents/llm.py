"""One model call, with what it cost.

Day 6's `structured._chat` returns the content and the elapsed time, which is
what Day 6 measured. Day 7 needs a third thing -- tokens -- because the budget is
denominated in them and because the fan-out measurement is only interpretable
next to how much work each branch actually did.

Rather than change a function whose behaviour Day 6's published numbers were
taken through, this is a separate, additive helper. It calls the same endpoint
the same way and adds usage accounting.

Why the native `/api/chat` and not the OpenAI-compatible `/v1`: `think: false`
is honoured by one and ignored by the other, and reasoning on `qwen3.5:9b` is a
15x difference in latency (ADR-009, ADR-015). None of Day 7's workers need a
chain of thought -- they classify, extract, and compare, all against text that is
already in front of them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from regops_retrieval.index import base_url

from regops_agents.budget import spent

MODEL = "qwen3.5:9b"
TIMEOUT_S = 300.0


@dataclass
class Reply:
    """One completion, and its bill."""

    content: str
    seconds: float
    in_tokens: int
    out_tokens: int
    error: str = ""

    def spend(self, *, steps: int = 1) -> dict:
        """This call as a state update the budget reducer can merge."""
        return spent(
            steps=steps,
            seconds=self.seconds,
            in_tokens=self.in_tokens,
            out_tokens=self.out_tokens,
        )


def chat(
    prompt: str,
    *,
    system: str = "",
    model: str = MODEL,
    schema: dict | None = None,
    temperature: float = 0.0,
    num_ctx: int | None = None,
) -> Reply:
    """A single completion. Never raises -- a dead endpoint is a `Reply` with an error.

    Workers run inside a graph that owns a budget and a partial-result contract.
    A worker that raises on a transport hiccup skips the accounting and turns a
    degraded run into no run, which is the shape Day 6 argued against for step
    ceilings and which applies here for the same reason.
    """
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    options: dict = {"temperature": temperature}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    payload: dict = {
        "model": model,
        "messages": messages,
        "think": False,
        "stream": False,
        "options": options,
    }
    if schema is not None:
        payload["format"] = schema

    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        body = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return Reply("", time.perf_counter() - t0, 0, 0, f"{type(exc).__name__}: {exc}")

    return Reply(
        content=(body.get("message", {}) or {}).get("content") or "",
        seconds=time.perf_counter() - t0,
        # Ollama reports both directions. `prompt_eval_count` is absent when the
        # prompt prefix was served from cache, which is a real saving and is
        # recorded as such rather than back-filled with an estimate.
        in_tokens=int(body.get("prompt_eval_count") or 0),
        out_tokens=int(body.get("eval_count") or 0),
    )
