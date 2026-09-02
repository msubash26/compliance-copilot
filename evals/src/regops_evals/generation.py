"""Answering the golden set, and then judging the answers with a second model.

This is the expensive half of Day 5 and the reason its scope is what it is.
Retrieval metrics for all 7 configurations over all 150 items cost about four
minutes. One answer costs 6.76s at the median, so one configuration is ~17
minutes and seven would be two hours *before* any judging. So the four ladder
rungs are measured over the full 150 and the three ablations are not measured
here at all -- an empty cell that says why is worth more than a cell filled from
20 samples and quoted as though it were 150 (ADR-021).

**Abstention is two rates, never one.** A single "abstention accuracy" flatters
any system that abstains constantly, and the two failures are not the same
failure:

- **false answer** on the 35 negatives -- the system answered a question this
  corpus cannot answer. In a compliance tool that is *dangerous*.
- **false abstention** on the 115 grounded items -- the system refused a question
  it had the clause for. That is *useless*.

Reporting only the first is how a system that says "I don't know" to everything
scores 100%.

**Batch by model.** Query vectors are taken first with `nomic-embed-text`
resident, then generation runs with only `qwen3.5:9b` touched, then judging
loads `qwen3.8` after generation is finished with the GPU. Interleaving them
costs a 17.7 GB swap per item -- the rule that cost Day 4 a rewrite of `verify`.
"""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx
from regops_retrieval.configs import BY_NAME, POOL, build
from regops_retrieval.context import assemble_context
from regops_retrieval.index import Index, base_url
from regops_retrieval.retrievers import QuestionVectors

from regops_evals.metrics import percentile
from regops_evals.schema import read_jsonl

TIMEOUT_S = 300.0
TOP_K = 5

# Published Bedrock on-demand rates for the comparator model, in USD per million
# tokens. These are an *assumption in a constant*, not a measurement: there are
# no AWS credentials on this box (Day 5 research 7), so the Bedrock column is
# computed from these rates against token counts that were measured locally.
# The estimate is linear in these two numbers, so a reader who has current rates
# can rescale the column without re-running anything. Checked 2026-09-05;
# re-check before quoting.
BEDROCK_COMPARATOR = "Claude Haiku 4.5 (Bedrock on-demand)"
BEDROCK_USD_PER_M_INPUT = 1.00
BEDROCK_USD_PER_M_OUTPUT = 5.00

ANSWER_PROMPT = """\
You are a regulatory compliance assistant answering questions about Singapore MAS notices and
guidelines. You are given numbered excerpts retrieved from the corpus.

{context}

Question: {question}

Rules:
- Answer ONLY from the excerpts above. Do not use your own knowledge of MAS regulation.
- Cite the excerpt numbers you used, e.g. [1] or [1, 3].
- If the excerpts do not answer the question, set "sufficient" to false and say what is missing.
  Refusing when the answer is genuinely absent is correct behaviour, not a failure.

Reply with exactly this JSON and nothing else:
{{"sufficient": true/false, "answer": "two or three sentences", "citations": [1, 2]}}"""

JUDGE_GROUNDED = """\
Excerpts given to an assistant:

{context}

Question: {question}

The assistant answered: {answer}
It cited excerpts: {citations}

Two separate judgements:
1. Is EVERY factual claim in that answer supported by the excerpts above? An answer that adds a
   requirement, a threshold or a deadline the excerpts do not state is NOT grounded, even if the
   addition is correct in reality.
2. Do the cited excerpt numbers actually contain the support for the answer?

Also say whether the assistant in effect refused to answer (said it could not answer, or that
the excerpts were insufficient), regardless of what it claimed.

Reply with exactly this JSON and nothing else:
{{"grounded": true/false, "citations_support": true/false, "refused": true/false,
  "why": "one short sentence"}}"""


@dataclass
class Answer:
    config: str
    item_id: str
    query_type: str
    flagged: bool
    is_negative: bool
    question: str
    context: str
    cited_uids: list[str]
    context_chars: int
    context_truncated: int
    context_dropped: int
    retrieval_s: float
    gen_s: float
    gpu_s: float
    prompt_tokens: int
    completion_tokens: int
    sufficient: bool
    abstained: bool
    answer: str
    citations: list[int] = field(default_factory=list)
    citations_in_range: bool = True
    error: str = ""


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _chat(model: str, prompt: str, *, num_predict: int = 400) -> tuple[dict | None, dict]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": num_predict},
    }
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        body = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return None, {"wall_s": time.perf_counter() - t0, "error": str(exc)[:200]}
    # Ollama reports nanoseconds. `prompt_eval + eval` is the GPU's share; wall
    # time also carries queueing and HTTP, which is not what "GPU-seconds per
    # query" should mean.
    meta = {
        "wall_s": time.perf_counter() - t0,
        "gpu_s": (body.get("prompt_eval_duration", 0) + body.get("eval_duration", 0)) / 1e9,
        "prompt_tokens": body.get("prompt_eval_count", 0),
        "completion_tokens": body.get("eval_count", 0),
        "error": "",
    }
    return _extract_json(body.get("message", {}).get("content") or ""), meta


def generate_answers(
    golden: Path,
    index: Path,
    *,
    config_names: list[str],
    model: str = "qwen3.5:9b",
    out_dir: Path = Path("results/day5/answers"),
    raw_dir: Path = Path("results/day5/raw"),
) -> int:
    items = read_jsonl(golden)
    ix = Index(index)
    vectors = QuestionVectors()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfgs = [BY_NAME[n] for n in config_names]
    if any(c.decompose for c in cfgs):
        # Decompositions come from the sweep's on-disk cache; if a ladder rung
        # ever decomposes, take them before the embedder loads.
        from regops_retrieval.decompose import Decomposer

        dec = Decomposer(Path("results/day5/decompositions"))
        vectors.warm(s for it in items for s in dec(it.question))

    t0 = time.perf_counter()
    vectors.warm(it.question for it in items)
    print(f"query vectors: {len(vectors)} embedded in {time.perf_counter() - t0:.0f}s")

    scorer = None
    if any(c.rerank for c in cfgs):
        from regops_retrieval import rerank as rr

        scorer = rr.load()
        print(f"cross-encoder on {scorer.device}")

    for cfg in cfgs:
        path = out_dir / f"{cfg.name}.jsonl"
        retriever = build(
            cfg, ix, vectors, scorer=scorer, decompose_dir=Path("results/day5/decompositions")
        )
        rows: list[Answer] = []
        started = time.perf_counter()
        for n, it in enumerate(items, 1):
            vectors.reset()
            t = time.perf_counter()
            hits = retriever.search(it.question, POOL)
            asm = assemble_context(ix, hits, mode=cfg.context_mode, top_k=TOP_K)
            retrieval_s = time.perf_counter() - t + vectors.replay_cost()

            obj, meta = _chat(model, ANSWER_PROMPT.format(context=asm.text, question=it.question))
            obj = obj or {}
            cites = [
                int(c) for c in obj.get("citations", []) if str(c).strip().lstrip("-").isdigit()
            ]
            sufficient = bool(obj.get("sufficient", False))
            rows.append(
                Answer(
                    config=cfg.name,
                    item_id=it.id,
                    query_type=it.query_type,
                    flagged=it.verification.status == "flagged",
                    is_negative=not it.gold_spans,
                    question=it.question,
                    context=asm.text,
                    cited_uids=asm.cited,
                    context_chars=asm.chars,
                    context_truncated=asm.truncated_excerpts,
                    context_dropped=asm.dropped_excerpts,
                    retrieval_s=round(retrieval_s, 4),
                    gen_s=round(meta["wall_s"], 4),
                    gpu_s=round(meta.get("gpu_s", 0.0), 4),
                    prompt_tokens=meta.get("prompt_tokens", 0),
                    completion_tokens=meta.get("completion_tokens", 0),
                    sufficient=sufficient,
                    # An empty or unparseable reply is not an abstention -- it is
                    # an error, and counting it as a refusal would credit a
                    # crashed generator with good judgement.
                    abstained=(not sufficient) and not meta.get("error"),
                    answer=str(obj.get("answer", ""))[:2000],
                    citations=cites,
                    citations_in_range=all(1 <= c <= len(asm.cited) for c in cites),
                    error=meta.get("error", "") or ("" if obj else "unparseable reply"),
                )
            )
            if n % 25 == 0:
                rate = (time.perf_counter() - started) / n
                print(
                    f"  {cfg.name} {n}/{len(items)}  {rate:.2f}s/item  "
                    f"eta {rate * (len(items) - n) / 60:.1f}min",
                    flush=True,
                )
        path.write_text("\n".join(json.dumps(asdict(r)) for r in rows) + "\n")
        print(
            f"{cfg.name}: {len(rows)} answers in {(time.perf_counter() - started) / 60:.1f}min "
            f"-> {path}"
        )
    return 0


def abstention_split(rows: list[dict]) -> dict:
    """The 2x2, and the same 2x2 split by whether the item is flagged.

    Abstention needs no judge -- it is mechanical, from the generator's own
    `sufficient` field -- so this lives apart from the judging pass and can be
    recomputed from an answers file at any time.

    The flagged split is the point. 28 of the 150 items are machine-verified but
    not human-reviewed, and if the system refuses those at several times the rate
    it refuses the rest, then part of what the "false abstention" column measures
    is the golden set rather than the retriever. That is worth publishing next to
    the number rather than discovering later.
    """
    neg = [r for r in rows if r["is_negative"]]
    pos = [r for r in rows if not r["is_negative"]]

    def rate(rs: list[dict], want: bool) -> float | None:
        return round(sum(1 for r in rs if r["abstained"] is want) / len(rs), 4) if rs else None

    fl = [r for r in pos if r["flagged"]]
    un = [r for r in pos if not r["flagged"]]
    return {
        "negatives_n": len(neg),
        "grounded_items_n": len(pos),
        # Dangerous: answered a question the corpus cannot answer.
        "false_answer_rate": rate([r for r in neg if not r["error"]], False) or 0.0,
        "correct_abstention_rate": rate(neg, True) or 0.0,
        # Useless: refused a question it had the clause for.
        "false_abstention_rate": rate(pos, True) or 0.0,
        "false_abstention_flagged": rate(fl, True),
        "false_abstention_unflagged": rate(un, True),
        "flagged_n": len(fl),
        "unflagged_n": len(un),
    }


# -- judging --------------------------------------------------------------


async def _ajudge(client: httpx.AsyncClient, model: str, prompt: str) -> dict | None:
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


def judge_answers(
    golden: Path,
    answers_dir: Path,
    *,
    model: str = "qwen3.8:latest",
    out: Path = Path("results/day5/generation.json"),
    concurrency: int = 3,
) -> int:
    files = sorted(answers_dir.glob("*.jsonl"))
    if not files:
        print(f"no answers under {answers_dir}; run generate-answers first")
        return 1

    loaded: dict[str, list[dict]] = {
        f.stem: [json.loads(x) for x in f.read_text().splitlines() if x.strip()] for f in files
    }
    total = sum(len(v) for v in loaded.values())
    print(f"judging {total} answers with {model} (not the model that wrote them)")

    # Only answered, grounded items need a groundedness judgement: an abstention
    # has no claims to support, and a negative has no gold answer to be grounded
    # in. Judging those anyway would spend 30% of the pass measuring nothing.
    work: list[tuple[str, dict]] = [
        (cfg, r)
        for cfg, rows in loaded.items()
        for r in rows
        if not r["is_negative"] and not r["abstained"] and not r["error"]
    ]
    verdicts: dict[tuple[str, str], dict] = {}

    async def run() -> None:
        sem = asyncio.Semaphore(concurrency)
        done = [0]

        async def one(client: httpx.AsyncClient, cfg: str, r: dict) -> None:
            async with sem:
                obj = await _ajudge(
                    client,
                    model,
                    JUDGE_GROUNDED.format(
                        context=r["context"][:12000],
                        question=r["question"],
                        answer=r["answer"],
                        citations=r["citations"] or "none",
                    ),
                )
                if obj is not None:
                    verdicts[(cfg, r["item_id"])] = obj
                done[0] += 1
                if done[0] % 50 == 0:
                    print(f"  judged {done[0]}/{len(work)}", flush=True)

        async with httpx.AsyncClient() as client:
            await asyncio.gather(*(one(client, c, r) for c, r in work))

    t0 = time.perf_counter()
    asyncio.run(run())

    report = {
        "judge": model,
        "answers_dir": str(answers_dir),
        "judged": len(verdicts),
        "judgeable": len(work),
        "wall_s": round(time.perf_counter() - t0, 1),
        "bedrock": {
            "comparator": BEDROCK_COMPARATOR,
            "usd_per_m_input": BEDROCK_USD_PER_M_INPUT,
            "usd_per_m_output": BEDROCK_USD_PER_M_OUTPUT,
        },
        "configs": {},
        "cost": {
            "rate_note": (
                f"{BEDROCK_COMPARATOR}, ${BEDROCK_USD_PER_M_INPUT:.2f}/M input and "
                f"${BEDROCK_USD_PER_M_OUTPUT:.2f}/M output, applied to locally measured token "
                "counts. No AWS call was made."
            ),
            "per_config": {},
        },
    }

    for cfg, rows in sorted(loaded.items()):
        pos = [r for r in rows if not r["is_negative"]]
        answered_pos = [r for r in pos if not r["abstained"] and not r["error"]]
        # Pair the verdict with its row rather than filtering two lists in
        # parallel: a judge call that failed drops one element from one list and
        # silently shifts every citation check onto the wrong answer.
        judged = [
            (r, v) for r in answered_pos if (v := verdicts.get((cfg, r["item_id"]))) is not None
        ]
        vs = [v for _, v in judged]

        errors = sum(1 for r in rows if r["error"])
        report["configs"][cfg] = {
            **abstention_split(rows),
            "answers": len(rows),
            "errors": errors,
            # Groundedness is over the answers that made a claim. Items where the
            # system abstained are counted in the abstention rates instead, so
            # this number is never inflated by silence.
            "groundedness": round(
                statistics.mean([1.0 if v.get("grounded") else 0.0 for v in vs]), 4
            )
            if vs
            else 0.0,
            "citation_valid": round(
                statistics.mean(
                    [
                        1.0 if (v.get("citations_support") and r["citations_in_range"]) else 0.0
                        for r, v in judged
                    ]
                ),
                4,
            )
            if judged
            else 0.0,
            "judge_says_refused_anyway": sum(1 for v in vs if v.get("refused")),
            "grounded_n": len(vs),
            "p50_s": round(percentile([r["gen_s"] for r in rows], 50), 3),
            "p95_s": round(percentile([r["gen_s"] for r in rows], 95), 3),
            "p50_end_to_end_s": round(
                percentile([r["gen_s"] + r["retrieval_s"] for r in rows], 50), 3
            ),
            "truncated_queries": sum(
                1 for r in rows if r["context_truncated"] or r["context_dropped"]
            ),
        }
        pt = statistics.mean(r["prompt_tokens"] for r in rows)
        ct = statistics.mean(r["completion_tokens"] for r in rows)
        report["cost"]["per_config"][cfg] = {
            "gpu_s_per_query": round(statistics.mean(r["gpu_s"] for r in rows), 3),
            "prompt_tokens": round(pt),
            "completion_tokens": round(ct),
            "bedrock_usd_per_1k_queries": round(
                1000 * (pt * BEDROCK_USD_PER_M_INPUT + ct * BEDROCK_USD_PER_M_OUTPUT) / 1_000_000,
                2,
            ),
        }
        g = report["configs"][cfg]
        print(
            f"{cfg:20s} grounded {g['groundedness']:.3f} (n={g['grounded_n']})  "
            f"false-answer {g['false_answer_rate']:.3f}  "
            f"false-abstention {g['false_abstention_rate']:.3f}  "
            f"p50 {g['p50_s']:.2f}s"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    # Persist the raw verdicts too. Judging is the expensive pass; re-deriving an
    # aggregate from it should not cost another 30 minutes of GPU.
    vpath = out.parent / "verdicts.json"
    vpath.write_text(
        json.dumps({f"{c}|{i}": v for (c, i), v in sorted(verdicts.items())}, indent=1) + "\n"
    )
    print(f"report -> {out}\nverdicts -> {vpath}")
    return 0
