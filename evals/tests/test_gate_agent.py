"""The gate, and the property that matters most: it can fail.

A gate never observed failing is a gate nobody knows the polarity of. Phase 5 of
the Day 8 plan proves that against the real pipeline by degrading a prompt and
watching the build reject it; this proves the same thing per-mechanism, in
milliseconds, with no GPU -- so the day the gate stops being able to fail, the
suite says so rather than the next regression saying so.

Every artifact here is synthetic. What is being tested is the comparison, not the
numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from regops_evals.gate_agent import dig, run_gate_agent, tasks_sha
from regops_evals.prompts import prompt_hash, prompt_hashes

ARM = "supervisor"


def artifact(tmp_path: Path, name: str, *, fresh: bool = True, **overrides) -> Path:
    metrics = {
        "success": {
            "composite": {"passed": 20, "n": 30},
            "retrieved_gold": {"passed": 24, "n": 30},
            "cited_resolvable": {"passed": 27, "n": 30},
            "abstained_correctly": {"passed": 26, "n": 30},
            "within_budget": {"passed": 30, "n": 30},
        },
        "abstention": {"false_answer": {"n": 5, "count": 1}},
        "tool_calls": {"recall_mean": 0.8, "precision_mean": 0.4, "errors": 2},
        "trajectory": {"efficiency_mean": 0.45},
        "citations": {"resolvable": 31, "unresolvable": 3},
        "cost": {"tokens": 120000},
        "latency": {"p50_s": 8.0, "p95_s": 20.0},
    }
    for path, value in overrides.items():
        keys = path.split(".")
        node = metrics
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value

    payload = {
        "arms": [ARM],
        "tasks": "golden/tasks/v1/tasks.jsonl",
        "n_tasks": 30,
        "prompt_hash": prompt_hash() if fresh else "0" * 64,
        "prompts": prompt_hashes() if fresh else {"workers.EXTRACT_PROMPT": "deadbeef"},
        "metrics": {ARM: metrics},
    }
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


@pytest.fixture
def no_task_file(tmp_path, monkeypatch):
    """The task-file check is exercised separately; here it must not fire."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_an_identical_fresh_artifact_passes(no_task_file):
    a = artifact(no_task_file, "eval.json")
    b = artifact(no_task_file, "baseline.json")
    assert run_gate_agent(a, b, arm=ARM) == 0


def test_an_improvement_passes(no_task_file):
    a = artifact(no_task_file, "eval.json", **{"success.composite.passed": 25})
    b = artifact(no_task_file, "baseline.json")
    assert run_gate_agent(a, b, arm=ARM) == 0


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("success.composite.passed", 19),
        ("success.retrieved_gold.passed", 23),
        ("success.cited_resolvable.passed", 26),
        ("success.abstained_correctly.passed", 25),
        ("success.within_budget.passed", 29),
        ("tool_calls.recall_mean", 0.79),
        ("citations.resolvable", 30),
    ],
)
def test_a_single_task_regressing_fails_the_build(no_task_file, path, value):
    """Exact, not 5%. The noise floor on every one of these was measured at zero."""
    a = artifact(no_task_file, "eval.json", **{path: value})
    b = artifact(no_task_file, "baseline.json")
    assert run_gate_agent(a, b, arm=ARM) == 1


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("citations.unresolvable", 4),
        ("abstention.false_answer.count", 2),
        ("tool_calls.errors", 3),
    ],
)
def test_a_metric_that_should_go_down_fails_when_it_goes_up(no_task_file, path, value):
    a = artifact(no_task_file, "eval.json", **{path: value})
    b = artifact(no_task_file, "baseline.json")
    assert run_gate_agent(a, b, arm=ARM) == 1


class TestLatency:
    """The one banded metric, because it is the one with measured variance (6.5%)."""

    def test_drift_inside_the_band_passes(self, no_task_file):
        a = artifact(no_task_file, "eval.json", **{"latency.p50_s": 9.9})  # +24%
        b = artifact(no_task_file, "baseline.json")
        assert run_gate_agent(a, b, arm=ARM) == 0

    def test_drift_beyond_the_band_fails(self, no_task_file):
        a = artifact(no_task_file, "eval.json", **{"latency.p50_s": 10.5})  # +31%
        b = artifact(no_task_file, "baseline.json")
        assert run_gate_agent(a, b, arm=ARM) == 1

    def test_getting_faster_never_fails(self, no_task_file):
        a = artifact(no_task_file, "eval.json", **{"latency.p50_s": 2.0})
        b = artifact(no_task_file, "baseline.json")
        assert run_gate_agent(a, b, arm=ARM) == 0


class TestStaleness:
    """The mechanism that makes 'change a prompt, push, and CI tells you' real."""

    def test_an_artifact_produced_before_a_prompt_change_fails(self, no_task_file):
        a = artifact(no_task_file, "eval.json", fresh=False)
        b = artifact(no_task_file, "baseline.json", fresh=False)
        assert run_gate_agent(a, b, arm=ARM) == 1

    def test_it_fails_even_when_every_metric_improved(self, no_task_file):
        """A better number measured against the old prompt is still not evidence."""
        a = artifact(no_task_file, "eval.json", fresh=False, **{"success.composite.passed": 30})
        b = artifact(no_task_file, "baseline.json", fresh=False)
        assert run_gate_agent(a, b, arm=ARM) == 1

    def test_a_changed_task_file_is_staleness_too(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        tasks = tmp_path / "tasks.jsonl"
        tasks.write_text('{"task_id": "t-001"}\n')
        a = artifact(tmp_path, "eval.json")
        payload = json.loads(a.read_text())
        payload["tasks_sha"] = tasks_sha(tasks)
        a.write_text(json.dumps(payload))
        b = artifact(tmp_path, "baseline.json")
        assert run_gate_agent(a, b, arm=ARM, tasks=tasks) == 0

        tasks.write_text('{"task_id": "t-001"}\n{"task_id": "t-002"}\n')
        assert run_gate_agent(a, b, arm=ARM, tasks=tasks) == 1


class TestDegenerate:
    def test_a_missing_artifact_fails_rather_than_passing_quietly(self, tmp_path):
        assert run_gate_agent(tmp_path / "nope.json", tmp_path / "also-nope.json") == 1

    def test_an_artifact_without_the_gated_arm_fails(self, no_task_file):
        a = artifact(no_task_file, "eval.json")
        payload = json.loads(a.read_text())
        payload["metrics"] = {"single_agent": payload["metrics"][ARM]}
        a.write_text(json.dumps(payload))
        assert run_gate_agent(a, no_task_file / "baseline.json", arm=ARM) == 1

    def test_a_first_run_with_no_baseline_passes_and_says_so(self, no_task_file, capsys):
        a = artifact(no_task_file, "eval.json")
        assert run_gate_agent(a, no_task_file / "absent.json", arm=ARM) == 0
        assert "ABSENT" in capsys.readouterr().out

    def test_dig_returns_none_rather_than_raising_on_a_missing_path(self):
        assert dig({"a": {"b": 1}}, ("a", "b")) == 1
        assert dig({"a": {"b": 1}}, ("a", "z")) is None
        assert dig({"a": 1}, ("a", "b")) is None
