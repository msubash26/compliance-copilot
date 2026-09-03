"""LangFuse tracing, opt-in and unable to take a run down with it.

Day 0 stood the stack up and Days 6 and 7 never wired it in; this is the module
that closes that. Two things about it are decisions rather than plumbing.

**The API is v4's, and v3's names are gone.** `start_as_current_span` and
`start_as_current_generation` -- which is what most published examples still
show -- do not exist on `langfuse` 4.15.1. There is one entry point,
`start_as_current_observation(name=..., as_type=...)`, and `as_type` carries the
distinction: `"span"` for a graph node, `"generation"` for a model call,
`"tool"` for an MCP call. Recording this because the migration is invisible until
runtime and the error is an `AttributeError` a long way from the cause.

**Tracing is not allowed to be a dependency of the measurement.** An eval harness
that cannot run when the observability stack is down has made observability a
prerequisite for knowing whether the system works, which is backwards. So the
tracer is off by default, every call is wrapped, and a LangFuse that is
unreachable degrades a traced run to an untraced one and says so once. Measured
overhead when it *is* on: 0.8 ms for a span with three nested generations,
against runs of five to sixty seconds.

**And it is not the measurement store.** This self-hosted v4 deployment runs in
`events_only` mode: `/api/public/traces`, `/observations` and `/scores` all
return 404 -- *"not available on deployments running in Langfuse v4 events_only
mode"*. Anything written here cannot be read back by the gate. Scores therefore
go to `results/day8/eval.json`, which is committed, and LangFuse gets the picture
a person looks at. A gate that reads a mutable store would not be reproducible
even where the endpoint exists.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from typing import Any, Protocol

# Naming, so the waterfall reads: a graph node is a span under its own name
# (`retrieve`), a model call is a generation named `llm:<worker>`, and an MCP call
# is a tool span under the server's own tool name. Without the prefix the node
# span and the generation inside it are both called `extract`, which is legible in
# a tree and useless in a list.
#
# Observation types, so a typo is an ImportError rather than a span quietly filed
# under the wrong kind.
SPAN = "span"
GENERATION = "generation"
TOOL = "tool"


class _Obs(Protocol):
    def update(self, **kwargs: Any) -> Any: ...


class Tracer(Protocol):
    """What the graph is allowed to ask for. Deliberately two methods."""

    enabled: bool

    def observe(self, name: str, *, as_type: str = SPAN, **kwargs: Any): ...

    def trace(self, name: str, **kwargs: Any): ...

    def flush(self) -> None: ...


class _NullObs:
    def update(self, **kwargs: Any) -> None:
        return None


class NullTracer:
    """The default. Every method is a no-op with the same signature."""

    enabled = False

    @contextlib.contextmanager
    def observe(self, name: str, *, as_type: str = SPAN, **kwargs: Any) -> Iterator[_NullObs]:
        yield _NullObs()

    @contextlib.contextmanager
    def trace(self, name: str, **kwargs: Any) -> Iterator[_NullObs]:
        yield _NullObs()

    def flush(self) -> None:
        return None


NULL: Tracer = NullTracer()


class LangfuseTracer:
    """A real one. Never raises out of `observe`; a broken tracer is not a broken run."""

    def __init__(self, client) -> None:
        self.client = client
        self.enabled = True
        self.dropped = 0

    @contextlib.contextmanager
    def observe(self, name: str, *, as_type: str = SPAN, **kwargs: Any):
        try:
            cm = self.client.start_as_current_observation(name=name, as_type=as_type, **kwargs)
        except Exception:  # noqa: BLE001
            self.dropped += 1
            yield _NullObs()
            return
        try:
            with cm as obs:
                yield obs
        except Exception:
            # The *body* raised. Re-raise it -- swallowing a worker's exception to
            # protect a trace would be the tracer changing the program.
            raise

    @contextlib.contextmanager
    def trace(self, name: str, **kwargs: Any):
        """One task, as the root of its own trace, named so the UI is readable."""
        with self.observe(name, as_type=SPAN, **kwargs) as obs:
            with contextlib.suppress(Exception):
                self.client.update_current_trace(name=name)
            yield obs

    def flush(self) -> None:
        with contextlib.suppress(Exception):
            self.client.flush()


def tracer(enabled: bool = True) -> Tracer:
    """A tracer, or the null one, with the reason printed once.

    Returns `NULL` rather than raising on every failure path -- no SDK, no keys,
    an unreachable host -- because the caller is an eval harness and the run is
    the point.
    """
    if not enabled:
        return NULL
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        print("trace: LANGFUSE_PUBLIC_KEY is unset; running untraced")
        return NULL
    try:
        from langfuse import get_client

        client = get_client()
        if not client.auth_check():
            print(f"trace: {os.environ.get('LANGFUSE_HOST', '?')} refused auth; running untraced")
            return NULL
    except Exception as exc:  # noqa: BLE001
        print(f"trace: unavailable ({type(exc).__name__}: {exc}); running untraced")
        return NULL
    return LangfuseTracer(client)


def usage(spend: dict) -> dict[str, int]:
    """Ollama's token counts in the shape LangFuse costs them in."""
    return {
        "input": int(spend.get("in_tokens", 0)),
        "output": int(spend.get("out_tokens", 0)),
        "total": int(spend.get("in_tokens", 0)) + int(spend.get("out_tokens", 0)),
    }
