"""The Postgres checkpointer, and the one thing it is here to prove.

The prep plan's Day 7 bullet is *"Postgres checkpointer so a run survives a
process restart and can be resumed"*. The claim worth making is the second half:
persistence that has never been read back by a **different process** is not
persistence, it is a cache with a network hop. `scripts/day7_resume.sh` starts a
run in one interpreter, exits it, and resumes in another; nothing is shared but
the database.

Notes that cost time to discover.

**Async, because the tools are.** `regdocs-mcp` reaches the agent over stdio and
its LangChain tools are coroutines -- a `StructuredTool` built from one refuses
sync invocation outright (Day 6). So the graph is driven with `astream` and the
saver has to be `AsyncPostgresSaver`; the sync `PostgresSaver` under an async
graph fails at the first write, not at compile.

**`setup()` is idempotent and cheap.** Measured at 0.01s against the running
container with the four tables already present, so it is called on every open
rather than guarded by a flag that would drift from the database.

**The connection hands back dicts, not tuples.** `psycopg` is configured with
`dict_row` by the saver, so a hand-written diagnostic query over `cp.conn` that
indexes a row by position raises `KeyError: 0` -- which reads like a missing
dictionary key from an unrelated layer. Index by name.

**No DSN means an in-memory saver.** CI has no Postgres and a test suite that
cannot run in CI is not a gate (ADR-002's rule about the `slow` marker applies
here for the same reason). The functions that need the real thing skip.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

DSN_ENV = "CHECKPOINTER_DSN"


def dsn() -> str:
    """The checkpointer DSN, from the environment or from `.env`.

    `.env` is read directly rather than through `python-dotenv`'s process-wide
    load: this is a library, and a library that mutates `os.environ` on import
    is a surprise waiting for whoever imports it second.
    """
    if os.environ.get(DSN_ENV):
        return os.environ[DSN_ENV]
    env = Path(__file__).resolve().parents[3] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == DSN_ENV:
                return value.strip().strip("'\"")
    return ""


@asynccontextmanager
async def checkpointer(*, required: bool = False) -> AsyncIterator:
    """An `AsyncPostgresSaver` if a DSN is available, an in-memory saver if not.

    `required=True` for the resume proof, where falling back to memory would
    make the demonstration vacuous -- the run would "survive" only because it
    never left the process.
    """
    url = dsn()
    if not url:
        if required:
            raise RuntimeError(
                f"{DSN_ENV} is not set and this call needs real persistence. "
                "Start the stack (`./scripts/stack.sh up`) or export the DSN."
            )
        from langgraph.checkpoint.memory import InMemorySaver

        yield InMemorySaver()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(url) as saver:
        await saver.setup()
        yield saver
