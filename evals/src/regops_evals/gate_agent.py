"""The gate: exact on quality, banded on latency, and able to fail on a stale run.

Day 8's central design problem is that the eval cannot run where the gate runs.
`gh api .../actions/runners` returns `total_count: 0` and GitHub's hosted runners
have no GPU, so an agent eval in CI would be a job that skips when there is no
model -- a green check mark that proves nothing, and this project wrote down on
Day 4 that a test which cannot run in CI is not a gate.

So the eval runs locally and commits `results/day8/eval.json`, and **CI gates the
artifact**, three ways:

1. **Staleness.** The artifact records a hash over every prompt and system
   message it was produced from, and a hash of the task file. CI recomputes both
   from the working tree. *A prompt changed and pushed without a re-run fails the
   build.* CI cannot measure the change; it can refuse to believe a number
   measured before it, which is what the prep plan's requirement actually needs.
2. **Comparison.** Every mechanical metric must be at least as good as
   `baseline.json`. See below for why "at least" and not "within 5%".
3. **Replay** -- `agents/tests/test_replay.py`, the graph over recorded tool
   results with a scripted model. It gates structure, not quality.

**Why exact rather than the prep plan's 5%.** Because the noise floor was
measured and it is zero. Ten tasks through the supervisor three times in one
process and once in a fresh interpreter: 0 of 10 items differed in route,
citations, steps, tokens or answer text, and the token total was identical to the
digit across all four runs -- 39,737. That is not luck. It is temperature 0,
`think: false`, Ollama's constrained decoding and two ranking-determinism fixes
that cost the better part of a day (ADR-022 here, ADR-008 in `regdocs-mcp`). A 5%
band on a metric whose variance is zero is fifty times looser than it needs to be
and would hide a single regressed task, which is exactly the resolution the
determinism work bought.

**Latency is the exception**, because it is the one thing that does move: 67.2s /
58.6s / 59.7s / 60.3s over the same four runs, a 6.5% spread. The band is 25%, so
it fires on a real change rather than on thermal drift or a warm model.

**One arm is gated.** All three are measured -- that keeps Day 7's comparison
alive as a regression surface for free -- but gating all three triples the ways a
build fails for reasons nobody is working on. The single agent and
plan-and-execute are reported.

**The judge does not gate.** Its verdicts are an uncalibrated model's opinion
until `golden/judge_calibration/` says otherwise, and a build that fails on that
fails for a reason nobody can audit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from regops_evals.prompts import compare, prompt_hash

# Metric -> (path into an arm's `metrics` block, direction).
# `up` means bigger is better and a drop fails. `down` means the opposite.
# Every one of these is mechanical: derived from the golden set, no model's
# opinion anywhere in it.
GATED: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("task success (all four outcomes)", ("success", "composite", "passed"), "up"),
    ("gold documents read", ("success", "retrieved_gold", "passed"), "up"),
    ("cited something resolvable", ("success", "cited_resolvable", "passed"), "up"),
    ("abstained correctly", ("success", "abstained_correctly", "passed"), "up"),
    ("finished within budget", ("success", "within_budget", "passed"), "up"),
    ("tool-call recall (mean)", ("tool_calls", "recall_mean"), "up"),
    ("resolvable citations", ("citations", "resolvable"), "up"),
    ("unresolvable citations", ("citations", "unresolvable"), "down"),
    ("answered a question the corpus cannot", ("abstention", "false_answer", "count"), "down"),
    ("tool-call errors", ("tool_calls", "errors"), "down"),
)

# Reported next to the gated rows and never enforced: precision punishes an
# architecture for reading broadly on purpose, p95 over thirty tasks is a single
# order statistic, and tokens are a cost story rather than a quality one.
REPORTED = (
    ("tool-call precision (mean)", ("tool_calls", "precision_mean")),
    ("trajectory efficiency (mean)", ("trajectory", "efficiency_mean")),
    ("tokens", ("cost", "tokens")),
    ("p95 latency", ("latency", "p95_s")),
)


def dig(d: dict, path: tuple[str, ...]):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def tasks_sha(path: Path) -> str:
    """The task file, hashed. Changing the tasks without re-running is staleness too."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fmt(v) -> str:
    if v is None:
        return "  --  "
    return f"{v:.4f}" if isinstance(v, float) else f"{v}"


def run_gate_agent(
    eval_path: Path,
    baseline_path: Path,
    *,
    arm: str = "supervisor",
    latency_tolerance: float = 0.25,
    tasks: Path | None = None,
) -> int:
    if not eval_path.exists():
        print(f"FAIL: no eval artifact at {eval_path}. Run `regops-evals agent-eval` locally.")
        return 1
    report = json.loads(eval_path.read_text())
    failures: list[str] = []

    # -- 1. staleness --------------------------------------------------------
    print(f"gate-agent  ·  {eval_path}  ·  arm '{arm}'\n")
    now = prompt_hash()
    was = report.get("prompt_hash", "")
    if now != was:
        moved = compare(report)
        failures.append(
            f"STALE: the prompts changed since this eval was produced "
            f"({was[:12] or 'absent'} -> {now[:12]}). Moved: {', '.join(moved) or 'unknown'}. "
            f"Re-run `regops-evals agent-eval` and commit the artifact."
        )
        print(f"  prompts      STALE   {was[:12] or 'absent'} -> {now[:12]}")
        for m in moved:
            print(f"               changed: {m}")
    else:
        print(f"  prompts      fresh   {now[:12]}  ({len(report.get('prompts') or {})} registered)")

    tasks_file = Path(tasks or report.get("tasks", "golden/tasks/v1/tasks.jsonl"))
    if tasks_file.exists():
        now_t = tasks_sha(tasks_file)
        was_t = report.get("tasks_sha", "")
        if now_t != was_t:
            failures.append(
                f"STALE: {tasks_file} changed since this eval was produced "
                f"({was_t[:12] or 'absent'} -> {now_t[:12]}). Re-run the eval."
            )
            print(f"  tasks        STALE   {was_t[:12] or 'absent'} -> {now_t[:12]}")
        else:
            print(f"  tasks        fresh   {now_t[:12]}  ({report.get('n_tasks')} tasks)")
    else:
        print(f"  tasks        SKIP    {tasks_file} not present")

    # -- 2. comparison -------------------------------------------------------
    metrics = (report.get("metrics") or {}).get(arm)
    if metrics is None:
        print(f"\nFAIL: the artifact has no '{arm}' arm; it measured {report.get('arms')}")
        return 1

    if not baseline_path.exists():
        print(f"\n  baseline     ABSENT  {baseline_path}")
        print("  Nothing to compare against. Copy this eval to the baseline to establish one.")
    else:
        base = (json.loads(baseline_path.read_text()).get("metrics") or {}).get(arm) or {}
        print(f"\n  {'metric':<44}{'baseline':>10}{'now':>10}   verdict")
        print("  " + "-" * 76)
        for label, path, direction in GATED:
            b, n = dig(base, path), dig(metrics, path)
            if b is None or n is None:
                print(f"  {label:<44}{_fmt(b):>10}{_fmt(n):>10}   skip (absent)")
                continue
            worse = (n < b) if direction == "up" else (n > b)
            if worse:
                failures.append(f"REGRESSION: {label} {b} -> {n}")
            print(f"  {label:<44}{_fmt(b):>10}{_fmt(n):>10}   {'FAIL' if worse else 'ok'}")

        # Latency, banded. The only currency with measured variance.
        b50, n50 = dig(base, ("latency", "p50_s")), dig(metrics, ("latency", "p50_s"))
        if b50 and n50:
            drift = (n50 - b50) / b50
            over = drift > latency_tolerance
            if over:
                failures.append(
                    f"REGRESSION: p50 latency {b50}s -> {n50}s "
                    f"({drift:+.0%}, tolerance {latency_tolerance:.0%})"
                )
            print(
                f"  {'p50 latency (banded)':<44}{b50:>10.2f}{n50:>10.2f}   "
                f"{'FAIL' if over else 'ok'}  {drift:+.0%} of {latency_tolerance:.0%}"
            )

        print("\n  reported, not gated (see the module docstring for why)")
        for label, path in REPORTED:
            print(f"  {label:<44}{_fmt(dig(base, path)):>10}{_fmt(dig(metrics, path)):>10}")

    # -- verdict -------------------------------------------------------------
    print()
    if failures:
        for f in failures:
            print(f"  {f}")
        print(f"\nGATE FAILED: {len(failures)} problem(s).")
        return 1
    print("GATE PASSED: the artifact is fresh and no mechanical metric regressed.")
    return 0
