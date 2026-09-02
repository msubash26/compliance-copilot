"""`regops-evals` -- build, verify and measure the golden set.

Four stages, each re-runnable and each persisting its output, because the
expensive parts differ: `select` spends 80s in the vector index, `generate`
spends four minutes on a GPU that has to be loaded with one model at a time, and
`verify` needs a second model loaded after the first is done with. Chaining them
in one process would mean paying for all of it to redo any of it.

    regops-evals select   --index index/regdocs.duckdb --out golden/v1/candidates.json
    regops-evals generate --candidates golden/v1/candidates.json --out golden/v1/golden.jsonl
    regops-evals verify   --index index/regdocs.duckdb --golden golden/v1/golden.jsonl
    regops-evals gate     --index index/regdocs.duckdb --golden golden/v1/golden.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from regops_evals.schema import STRATIFICATION


def _index(path: Path):
    from regops_evals.corpus import Index

    if not path.exists():
        sys.exit(f"error: no index at {path}")
    return Index(path)


def cmd_select(a: argparse.Namespace) -> int:
    from regops_evals.select import select_all

    ix = _index(a.index)
    targets = dict(STRATIFICATION)
    if a.limit:
        targets = {
            k: max(1, round(v * a.limit / sum(STRATIFICATION.values()))) for k, v in targets.items()
        }
    sel = select_all(ix, targets, seed=a.seed)

    payload = {
        "seed": a.seed,
        "targets": targets,
        "candidates": {
            qt: [
                {
                    "query_type": c.query_type,
                    "near_dups": c.near_dups,
                    "band": c.band,
                    "entity": c.entity,
                    "hint": c.hint,
                    "clauses": [
                        {
                            "doc_id": cl.doc_id,
                            "section_path": cl.section_path,
                            "heading": cl.heading,
                            "text": cl.text,
                            "title": cl.title,
                            "doc_type": cl.doc_type,
                            "effective_date": cl.effective_date,
                        }
                        for cl in c.clauses
                    ],
                }
                for c in cands
            ]
            for qt, cands in sel.items()
        },
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    for qt, cands in sel.items():
        flag = "" if len(cands) >= targets[qt] else f"  SHORT by {targets[qt] - len(cands)}"
        print(f"  {qt:16s} {len(cands):3d}/{targets[qt]}{flag}")
    print(f"wrote {a.out}")
    return 0


def cmd_generate(a: argparse.Namespace) -> int:
    from regops_evals.generate import generate_all

    return generate_all(
        a.candidates,
        a.out,
        index=a.index,
        model=a.model,
        trace_sample=a.trace_sample,
        concurrency=a.concurrency,
    )


def cmd_verify(a: argparse.Namespace) -> int:
    from regops_evals.verify import run_verify

    return run_verify(
        a.golden, a.index, model=a.model, judge=a.judge, queue=a.queue, report=a.report
    )


def cmd_gate(a: argparse.Namespace) -> int:
    from regops_evals.gate import run_gate

    return run_gate(a.golden, a.index, k=a.k, out=a.out)


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    ap = argparse.ArgumentParser(prog="regops-evals", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("select", help="choose candidate clauses, stratified by difficulty")
    s.add_argument("--index", type=Path, required=True)
    s.add_argument("--out", type=Path, default=Path("golden/v1/candidates.json"))
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--limit", type=int, default=None, help="scale all targets to this total")
    s.set_defaults(fn=cmd_select)

    g = sub.add_parser("generate", help="write questions and answers from candidates")
    g.add_argument("--candidates", type=Path, required=True)
    g.add_argument("--out", type=Path, default=Path("golden/v1/golden.jsonl"))
    g.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    g.add_argument("--model", default="qwen3.5:9b")
    g.add_argument("--concurrency", type=int, default=4)
    g.add_argument("--trace-sample", type=float, default=0.1)
    g.set_defaults(fn=cmd_generate)

    v = sub.add_parser("verify", help="mechanical checks, span drift, and an independent judge")
    v.add_argument("--index", type=Path, required=True)
    v.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    v.add_argument("--model", default="qwen3.8:latest", help="the verifier -- not the generator")
    v.add_argument(
        "--judge",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="--no-judge runs mechanical and drift checks only (CI has no GPU)",
    )
    v.add_argument("--queue", type=Path, default=None, help="write the review queue here")
    v.add_argument("--report", type=Path, default=None, help="write the check report JSON here")
    v.set_defaults(fn=cmd_verify)

    q = sub.add_parser("gate", help="measure BM25 and dense recall over the finished set")
    q.add_argument("--index", type=Path, required=True)
    q.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    q.add_argument("--k", type=int, default=5)
    q.add_argument("--out", type=Path, default=None)
    q.set_defaults(fn=cmd_gate)

    args = ap.parse_args()
    sys.exit(args.fn(args))
