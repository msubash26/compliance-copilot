"""The staleness hash: sensitive to the right edit, insensitive to the wrong one.

Risk 2 of the Day 8 plan, and it is the risk that quietly kills a gate: *the hash
is too sensitive and every commit turns red*. A gate that is red for reasons
nobody is working on gets switched off within a week, and then the build is green
for a reason nobody can state. So both halves are asserted here -- a docstring
edit must not move the hash, a prompt edit must.

The third test is the one that keeps the mechanism honest over time: a prompt
added to a worker and never registered is invisible to the gate, and that failure
has no symptom at all. The scan makes it break where the prompt is written.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from regops_evals import prompts

ROOT = Path(__file__).resolve().parents[2]


def test_the_hash_is_stable_across_calls():
    assert prompts.prompt_hash() == prompts.prompt_hash()


def test_every_registered_prompt_is_a_non_empty_string():
    texts = prompts.prompt_texts()
    assert len(texts) == sum(len(v) for v in prompts.REGISTRY.values())
    for name, text in texts.items():
        assert text.strip(), name


def test_editing_a_prompt_moves_the_hash(monkeypatch):
    import regops_agents.workers as workers

    before = prompts.prompt_hash()
    monkeypatch.setattr(workers, "EXTRACT_PROMPT", workers.EXTRACT_PROMPT + "\nBe concise.")
    assert prompts.prompt_hash() != before
    assert prompts.compare({"prompts": {**prompts.prompt_hashes()}}) == []


def test_editing_a_docstring_does_not_move_the_hash(monkeypatch):
    """The whole reason this hashes strings rather than files."""
    import regops_agents.workers as workers

    before = prompts.prompt_hash()
    monkeypatch.setattr(workers, "__doc__", "a completely different docstring")
    assert prompts.prompt_hash() == before


def test_the_gate_names_which_prompt_moved(monkeypatch):
    import regops_agents.workers as workers

    recorded = {"prompts": prompts.prompt_hashes()}
    monkeypatch.setattr(workers, "SYNTH_PROMPT", "something else entirely")
    assert prompts.compare(recorded) == ["workers.SYNTH_PROMPT"]


def test_swapping_two_prompts_moves_the_hash(monkeypatch):
    """A digest over concatenated bodies alone would not notice this."""
    import regops_agents.workers as workers

    before = prompts.prompt_hash()
    a, b = workers.EXTRACT_PROMPT, workers.GAP_PROMPT
    monkeypatch.setattr(workers, "EXTRACT_PROMPT", b)
    monkeypatch.setattr(workers, "GAP_PROMPT", a)
    assert prompts.prompt_hash() != before


def _module_constants(path: Path) -> set[str]:
    """Top-level `NAME = "a string"` assignments that look like prompts."""
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or not prompts.CONSTANT.match(target.id):
                continue
            if (
                isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                or isinstance(node.value, ast.JoinedStr | ast.BinOp | ast.Call)
            ):
                found.add(target.id)
    return found


MODULE_FILES = {
    "regops_agents.workers": ROOT / "agents/src/regops_agents/workers.py",
    "regops_agents.agent": ROOT / "agents/src/regops_agents/agent.py",
    "regops_evals.agentjudge": ROOT / "evals/src/regops_evals/agentjudge.py",
}


@pytest.mark.parametrize("module", sorted(MODULE_FILES))
def test_every_prompt_constant_in_the_agents_is_registered(module):
    """A prompt the gate cannot see is the one way this mechanism fails silently."""
    found = _module_constants(MODULE_FILES[module])
    registered = set(prompts.REGISTRY[module])
    missing = found - registered
    assert not missing, (
        f"{module} defines {sorted(missing)}, which reaches a model and is not in "
        "prompts.REGISTRY. Register it, or the staleness gate will never notice it changing."
    )


def test_the_registry_names_only_modules_that_exist():
    for module in prompts.REGISTRY:
        assert module in MODULE_FILES, f"{module} is registered but this test cannot scan it"
