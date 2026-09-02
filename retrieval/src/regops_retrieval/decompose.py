"""Query decomposition, paid for once.

One LLM call turns a question into the sub-questions a retriever should actually
run. It is cached on disk by the SHA-256 of the question, so the 150 calls are
paid once and every configuration that needs them reuses the *same*
decompositions -- which matters for more than time. If C7 were re-decomposed on
a second run, a difference between runs could be a difference in the
decomposer's sampling rather than in the retriever, and the determinism test
would fail for a reason that has nothing to do with the thing under test.

The cache is a plain JSON file per question, committed nowhere and rebuilt from
the model on demand.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import httpx

from regops_retrieval.index import base_url

MODEL = "qwen3.5:9b"
TIMEOUT_S = 180.0

PROMPT = """\
A compliance officer asked this question about Singapore MAS regulation:

{question}

Break it into the 1-3 separate lookups a search system would need to answer it. If the question
is a single lookup, return it once, unchanged in meaning. Each sub-question must stand alone --
no "it", no "the above". Do not invent notice numbers or paragraph numbers.

Reply with exactly this JSON and nothing else:
{{"sub_questions": ["...", "..."]}}"""


def _key(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]


class Decomposer:
    """Callable: question -> sub-questions. Disk-cached, deterministic."""

    def __init__(self, cache_dir: Path, model: str = MODEL) -> None:
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.calls = 0
        self.hits = 0
        # Seconds the decomposition call cost, replayed on a cache hit so C7's
        # latency column carries the price of decomposing rather than the price
        # of having decomposed yesterday.
        self.last_seconds = 0.0

    def __call__(self, question: str) -> list[str]:
        path = self.dir / f"{_key(question)}.json"
        if path.exists():
            self.hits += 1
            obj = json.loads(path.read_text())
            self.last_seconds = float(obj.get("seconds", 0.0))
            return obj["sub_questions"]
        t0 = time.perf_counter()
        subs = self._ask(question)
        self.last_seconds = time.perf_counter() - t0
        path.write_text(
            json.dumps(
                {
                    "question": question,
                    "sub_questions": subs,
                    "seconds": round(self.last_seconds, 3),
                },
                indent=1,
            )
        )
        return subs

    def _ask(self, question: str) -> list[str]:
        self.calls += 1
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": PROMPT.format(question=question)}],
            "think": False,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 300},
        }
        try:
            r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content") or ""
            obj = json.loads(raw) if raw.strip().startswith("{") else _loose(raw)
            subs = [str(s).strip() for s in (obj or {}).get("sub_questions", []) if str(s).strip()]
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            subs = []
        # A failed decomposition degrades to the original question rather than
        # to an empty result: the ablation must measure decomposition's effect,
        # not the model's availability.
        return subs[:3] or [question]


def _loose(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
