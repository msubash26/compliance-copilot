"""Day 0 (B3) — hello-world trace: local Ollama, traced to self-hosted LangFuse.

Deliberately calls Ollama rather than a hosted API. The air-gapped claim (ADR-005) has to hold
from the very first traced call, otherwise the observability plane quietly becomes the thing
that leaks. Nothing here reaches the public internet: Ollama is on localhost, LangFuse is the
local container stack, and `TELEMETRY_ENABLED=false` keeps LangFuse itself from phoning home.

Run:  uv run python scripts/hello_trace.py
Done when a trace with latency and token counts is visible at $LANGFUSE_HOST.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langfuse import get_client
from langfuse.openai import OpenAI  # drop-in for openai.OpenAI; emits a generation per call

QUESTION = (
    "In one sentence: what is the purpose of a regulatory notice issued by a financial "
    "supervisor such as MAS?"
)

# qwen3.5 is a reasoning model: thinking tokens are billed to the completion budget and arrive
# in a separate `reasoning` field, so a limit sized for the visible answer alone silently
# returns empty content with finish_reason="length". Budget for both.
#
# Thinking cannot be switched off over the OpenAI-compatible endpoint — neither
# `extra_body={"think": False}` nor `reasoning_effort` is honoured. Ollama's native
# /api/chat does honour `think: false`, and on this question that is 52 completion tokens in
# 0.8s versus 1140 in 13.1s. That gap is a Day 9 routing concern, not a Day 0 one: this script
# stays on the compat path because it is what langfuse.openai instruments automatically.
# See ADR-009.
MAX_TOKENS = 2048


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"error: {name} is not set. Copy .env.example to .env and fill it in.")
    return value


def ask(client: OpenAI, model: str, question: str) -> str:
    """One traced completion. The caller's span is the parent; the SDK nests the generation."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise regulatory-compliance assistant."},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        max_tokens=MAX_TOKENS,
        # Surfaces in the LangFuse UI so this trace is identifiable among later agent runs.
        metadata={"day": "0", "task": "B3", "stack": "local-ollama"},
    )
    choice = response.choices[0]
    usage = response.usage
    if usage is not None:
        print(
            f"  tokens: prompt={usage.prompt_tokens} "
            f"completion={usage.completion_tokens} total={usage.total_tokens}"
        )
    reasoning = (getattr(choice.message, "model_extra", None) or {}).get("reasoning")
    if reasoning:
        print(f"  reasoning: {len(reasoning)} chars (not counted in the answer below)")
    content = choice.message.content or ""
    if not content and choice.finish_reason == "length":
        sys.exit(
            f"error: model returned no content — the {MAX_TOKENS}-token budget was consumed "
            "by reasoning. Raise MAX_TOKENS."
        )
    return content


def main() -> int:
    load_dotenv()

    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OLLAMA_SMALL_MODEL", "qwen3.5:9b")
    _require("LANGFUSE_PUBLIC_KEY")
    _require("LANGFUSE_SECRET_KEY")

    langfuse = get_client()
    if not langfuse.auth_check():
        sys.exit(
            f"error: LangFuse rejected the credentials at {host}.\n"
            "       Is the stack up? ./scripts/stack.sh ps"
        )
    print(f"✓ LangFuse reachable at {host}")

    # api_key is required by the OpenAI client but ignored by Ollama.
    client = OpenAI(base_url=base_url, api_key=os.getenv("OLLAMA_API_KEY", "ollama"))
    print(f"→ asking {model} via {base_url}")

    # get_current_trace_id() only resolves inside an active span, so read it in the block.
    with langfuse.start_as_current_observation(name="hello-trace", as_type="span"):
        answer = ask(client, model, QUESTION)
        trace_id = langfuse.get_current_trace_id()
    print(f"\n{answer.strip()}\n")

    # Traces are batched and sent async; without this the process can exit first.
    langfuse.flush()

    if trace_id:
        print(f"✓ trace {trace_id}\n  {host}/trace/{trace_id}")
    else:
        print(f"✓ trace sent — see {host}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
