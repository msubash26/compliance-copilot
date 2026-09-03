"""Every prompt the agents run on, hashed, so a stale eval cannot pass the gate.

This is the mechanism that turns the prep plan's requirement -- *"you can change
a prompt, push, and have CI tell you whether you made it worse"* -- into
something real on a machine with no GPU in CI. The eval runs locally and commits
`results/day8/eval.json`; CI recomputes this hash from the working tree and fails
if it differs from the one the artifact recorded. **A prompt changed and pushed
without a re-run therefore fails the build.** CI cannot measure the change, but
it can refuse to believe a number that was measured before it.

**It hashes the strings, not the files**, and that is the whole design. Hashing
`workers.py` would turn every docstring edit red, and a gate that is red for
reasons nobody is working on gets switched off within a week. So this is an
explicit registry of the prompt and system-message constants, imported by name.
`test_prompts.py` asserts both halves: editing a docstring does not move the
hash, editing a prompt does.

**The registry is the failure mode.** A prompt added to a worker and not added
here is invisible to the gate, which is the one way this can quietly stop
working. `test_prompts.py::test_every_prompt_constant_in_the_agents_is_registered`
scans the modules for `*_PROMPT` / `*_SYSTEM` / `JUDGE_*` names and fails on one
that is missing, so adding a prompt without registering it breaks the build at
the point the prompt is written rather than the next time someone wonders why
the gate never fires.
"""

from __future__ import annotations

import hashlib
import importlib
import re

# module -> the constants in it that reach a model. Declared, not discovered, so
# that what the gate covers is reviewable in one place.
REGISTRY: dict[str, tuple[str, ...]] = {
    "regops_agents.workers": (
        "ROUTER_SYSTEM",
        "ROUTER_PROMPT",
        "EXTRACT_PROMPT",
        "GAP_PROMPT",
        "SYNTH_PROMPT",
    ),
    "regops_agents.agent": ("SYSTEM",),
    "regops_evals.agentjudge": ("JUDGE_SYSTEM", "JUDGE_PROMPT"),
}

# What the scan looks for when checking the registry is complete.
CONSTANT = re.compile(r"^(?:[A-Z][A-Z0-9_]*_)?(?:PROMPT|SYSTEM|RUBRIC)[A-Z0-9_]*$")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def prompt_texts() -> dict[str, str]:
    """Every registered prompt, keyed `module.CONSTANT`, in registry order."""
    out: dict[str, str] = {}
    for mod_name, names in REGISTRY.items():
        mod = importlib.import_module(mod_name)
        for name in names:
            value = getattr(mod, name)
            if not isinstance(value, str):
                raise TypeError(f"{mod_name}.{name} is {type(value).__name__}, not a prompt")
            out[f"{mod_name.split('.')[-1]}.{name}"] = value
    return out


def prompt_hashes() -> dict[str, str]:
    """Per-prompt digests, truncated. The gate names *which* prompt moved."""
    return {k: _sha(v)[:12] for k, v in prompt_texts().items()}


def prompt_hash() -> str:
    """One digest over all of them, order-stable and name-included.

    The name is hashed alongside the text so that renaming a constant -- or
    swapping two prompts' contents -- moves the hash. A digest over concatenated
    bodies alone would not.
    """
    joined = "\n\x00".join(f"{k}\x01{v}" for k, v in sorted(prompt_texts().items()))
    return _sha(joined)


def stamp() -> dict:
    """What an eval artifact records about the prompts it was produced from."""
    return {"prompt_hash": prompt_hash(), "prompts": prompt_hashes()}


def compare(recorded: dict) -> list[str]:
    """Which prompts moved since the artifact was written. Empty means fresh."""
    now = prompt_hashes()
    was = recorded.get("prompts") or {}
    moved = [k for k in sorted(set(now) | set(was)) if now.get(k) != was.get(k)]
    return moved
