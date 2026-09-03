"""One LangFuse trace, rendered as a waterfall, read from LangFuse's own store.

The Day 8 plan asks for a screenshot of the dashboard, and research 2 explains why
this file exists beside it: this self-hosted **LangFuse v4 deployment runs in
`events_only` mode**, so `/api/public/traces`, `/observations` and `/scores` all
return 404 -- *"not available on deployments running in Langfuse v4 events_only
mode"*. There is no read API to pull a trace from, and a rendering assembled from
the agent's own logs would prove only that the agent kept logs.

So this reads **ClickHouse**, which is where the LangFuse worker actually put the
spans. What it renders is therefore evidence that ingestion worked and that the
span tree has the shape the graph has -- in particular that the fan-out's branches
are **siblings**, which is the picture that shows Day 7's 1.00x speedup rather
than arguing it.

It is a diagnostic, not a product: the dashboard is the thing a person looks at,
and `docs/langfuse.md` says how to get there.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

CH_URL = os.environ.get("CLICKHOUSE_HTTP", "http://localhost:8123")
CH_USER = os.environ.get("CLICKHOUSE_USER", "clickhouse")

COLUMNS = (
    "span_id, parent_span_id, name, type, start_time, end_time, "
    "usage_details['input'], usage_details['output']"
)


def query(sql: str) -> list[list[str]]:
    r = httpx.post(
        CH_URL,
        content=sql,
        auth=(CH_USER, os.environ.get("CLICKHOUSE_PASSWORD", "")),
        timeout=30.0,
    )
    r.raise_for_status()
    return [line.split("\t") for line in r.text.strip().splitlines() if line]


def latest_trace(name_like: str) -> str | None:
    rows = query(
        "SELECT trace_id FROM events_core WHERE name LIKE "
        f"'{name_like}' ORDER BY start_time DESC LIMIT 1 FORMAT TSV"
    )
    return rows[0][0] if rows else None


def render(trace_id: str, width: int = 46) -> str:
    rows = query(
        f"SELECT {COLUMNS} FROM events_core WHERE trace_id = '{trace_id}' "
        "ORDER BY start_time FORMAT TSV"
    )
    if not rows:
        return f"no spans for trace {trace_id}\n"

    import datetime as dt

    def ts(s: str) -> float:
        return dt.datetime.fromisoformat(s).timestamp()

    spans = []
    for span_id, parent, name, kind, start, end, tin, tout in rows:
        spans.append(
            {
                "id": span_id,
                "parent": parent,
                "name": name,
                "type": kind,
                "t0": ts(start),
                "t1": ts(end) if end else ts(start),
                "in": int(tin or 0),
                "out": int(tout or 0),
            }
        )
    t0 = min(s["t0"] for s in spans)
    total = max(s["t1"] for s in spans) - t0 or 1.0

    kids: dict[str, list[dict]] = {}
    for s in spans:
        kids.setdefault(s["parent"], []).append(s)
    roots = [s for s in spans if s["parent"] not in {x["id"] for x in spans}]

    out: list[str] = []

    def walk(s: dict, depth: int) -> None:
        a = int((s["t0"] - t0) / total * width)
        b = max(a + 1, int((s["t1"] - t0) / total * width))
        bar = " " * a + "#" * (b - a)
        tokens = f"{s['in'] + s['out']:>6,}" if (s["in"] or s["out"]) else "      "
        label = "  " * depth + s["name"]
        out.append(
            f"{label:<40}{s['type']:<11}{s['t1'] - s['t0']:>7.2f}s {tokens}  |{bar:<{width}}|"
        )
        for k in sorted(kids.get(s["id"], []), key=lambda x: x["t0"]):
            walk(k, depth + 1)

    for r in sorted(roots, key=lambda x: x["t0"]):
        walk(r, 0)
    header = (
        f"{'span':<40}{'type':<11}{'elapsed':>8} {'tokens':>6}  |{'0s':<{width // 2}}{total:.1f}s|"
    )
    return "\n".join([f"trace {trace_id}", "", header, "-" * (60 + width), *out, ""])


def main(argv: list[str] | None = None) -> int:
    # The ClickHouse credentials live in the repo `.env` alongside LangFuse's own,
    # and this module is run directly rather than through `regops-evals`, which
    # loads it. Without this the query is a bare 403 that reads like a bug.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", default=None, help="trace id; default is the latest match")
    ap.add_argument("--name", default="supervisor · t-9%", help="LIKE pattern for --trace lookup")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    trace_id = a.trace or latest_trace(a.name)
    if not trace_id:
        print(f"no trace matching {a.name!r} in ClickHouse")
        return 1
    text = render(trace_id)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)
        print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
