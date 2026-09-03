"""Twenty hand-scored examples, and the boundary they are not allowed to cross.

This is the one part of Day 8 a machine cannot do, and the one place this project
has been most careful for the longest. `golden/v1` carries
`verification.human_reviewed: false` on all 150 items and
`evals/tests/test_golden_set.py` asserts it, because ADR-017 draws an explicit
line around what a machine-built set may claim. An agreement study that quietly
promoted twenty of those items would dissolve the boundary it was measuring
against.

So the hand-scores are a **separate artifact** under `golden/judge_calibration/`,
with their own provenance and their own README. They are never merged into
`golden/v1`, and they are never used to relabel an item. What they license is
exactly one sentence -- *"the judge agrees with a human N times out of 20, and
here is where it does not"* -- and that sentence is worth more than any other this
day can produce.

**Selection is deliberately biased toward disagreement.** Twenty examples on which
the judge and the mechanical checks already agree measure nothing: they would
report a high agreement rate that is an artifact of picking easy cases. So the
contested rows come first -- the judge passed all three axes on a task the
mechanical outcomes failed, or refused one they passed -- and a stratified fill
follows only if there are fewer than twenty. The sample is therefore **not
representative**, and the write-up has to say so: an agreement rate measured on
the hard cases is a *lower bound*, which is the useful direction to be wrong in.

**If the scoring does not happen, the claim is absent, not estimated.**
`report()` says "uncalibrated" and quotes no number. That was written into the
plan before the work started, for the obvious reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from regops_evals.agentjudge import AXES

# The plan's number. Twenty is about 45 minutes of reading clauses.
TARGET = 20


@dataclass
class Item:
    """One (task, arm) pair, its evidence, the judge's verdict, and a blank for a human."""

    task_id: str
    arm: str
    question: str
    answer: str
    cited_uids: list[str]
    gold_uids: list[str]
    mechanical: dict
    judge: dict
    contested: bool
    human: dict  # {axis: true|false}, empty until a person fills it in
    human_note: str = ""

    def scored(self) -> bool:
        return all(isinstance(self.human.get(a), bool) for a in AXES)


def _mechanical(row: dict) -> dict:
    return {
        "success": bool(row["success"]),
        "retrieved_gold": bool(row["retrieved_gold"]),
        "cited_resolvable": bool(row["cited_resolvable"]),
        "abstained_correctly": bool(row["abstained_correctly"]),
    }


def _contested(mech: dict, judge: dict) -> bool:
    """The judge and the mechanical checks reach opposite overall verdicts.

    Not a subtle definition on purpose: the point is to find the rows where one
    of the two is wrong, and a human is the only thing that can say which.
    """
    judge_ok = all(judge.get(a) for a in AXES)
    return judge_ok != mech["success"]


def select(
    report: dict, *, target: int = TARGET, arms: tuple[str, ...] | None = None
) -> list[Item]:
    """Contested rows first, then a stratified fill, deterministically."""
    arms = arms or tuple(report.get("arms", []))
    verdicts: dict[tuple[str, str], dict] = {}
    for arm, vs in (report.get("judge_rows") or {}).items():
        for v in vs:
            verdicts[(arm, v["task_id"])] = v

    items: list[Item] = []
    for arm in arms:
        for row in report.get("rows", {}).get(arm, []):
            v = verdicts.get((arm, row["task_id"]))
            if v is None or v.get("error"):
                continue  # unjudged rows have nothing to agree or disagree about
            judge = {a: bool(v[a]) for a in AXES}
            mech = _mechanical(row)
            items.append(
                Item(
                    task_id=row["task_id"],
                    arm=arm,
                    question=row["question"],
                    answer=row["answer"],
                    cited_uids=list(row["cited_uids"]),
                    gold_uids=list(row["gold_uids"]),
                    mechanical=mech,
                    judge=judge | {"why": v.get("why", "")},
                    contested=_contested(mech, judge),
                    human={},
                )
            )

    # Contested first, then a stratified fill by query type through the rest, and
    # a stable key throughout so re-running picks the same twenty.
    contested = sorted((i for i in items if i.contested), key=lambda i: (i.task_id, i.arm))
    rest = sorted((i for i in items if not i.contested), key=lambda i: (i.task_id, i.arm))
    return (contested + rest)[:target]


def write(items: list[Item], out: Path, worksheet: Path | None = None, index=None) -> None:
    """The machine-readable file, and the worksheet a person actually reads."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(i.__dict__, ensure_ascii=False) for i in items) + "\n")
    if worksheet is None:
        return

    lines = [
        "# Judge calibration worksheet",
        "",
        f"{len(items)} items, {sum(i.contested for i in items)} of them contested -- the judge and",
        "the mechanical checks reached opposite verdicts. Score each axis yourself **before**",
        "reading the judge's reasoning, then copy your three booleans into the matching line of",
        "`items.jsonl` under `human`. Nothing here changes `golden/v1` (ADR-017).",
        "",
        "- **supported** -- is every claim in the answer stated in the clauses below?",
        "- **complete** -- does it cover what the gold clauses state?",
        "- **cited_correctly** -- are the clauses cited the ones the support came from?",
        "",
    ]
    for n, i in enumerate(items, 1):
        lines += [
            f"## {n}. {i.task_id} · {i.arm}" + ("  · **contested**" if i.contested else ""),
            "",
            f"**Question.** {i.question}",
            "",
            f"**Answer.** {i.answer.strip()}",
            "",
            f"**Cited.** {', '.join(i.cited_uids) or '(nothing)'}",
            f"**Gold.** {', '.join(i.gold_uids) or '(none -- this question has no answer here)'}",
            "",
        ]
        if index is not None:
            for uid in i.cited_uids[:4]:
                clause = index.clause_by_uid(uid)
                body = (clause.text or "")[:1200] if clause else "NOT IN THE INDEX"
                title = (clause.title if clause else "") or uid
                # `>` rather than `> ` on the blank line, and the same inside the
                # body: a trailing space is invisible here and the repo's
                # pre-commit hook strips it, which would make every regeneration
                # of this file a diff against itself.
                quoted = "\n".join(f"> {ln}".rstrip() for ln in body.splitlines() or [""])
                lines += [f"> **{title} · {uid}**", ">", quoted, ""]
        lines += [
            f"_mechanical:_ `{json.dumps(i.mechanical)}`",
            "",
            "```json",
            '{"supported": null, "complete": null, "cited_correctly": null}',
            "```",
            "",
            "---",
            "",
        ]
    worksheet.parent.mkdir(parents=True, exist_ok=True)
    # Normalise the joined text, not the list: an element here can be a whole
    # answer with newlines inside it, and one of them was two spaces on a line of
    # its own. The repo's pre-commit hook would strip it and make every
    # regeneration a diff against itself.
    text = "\n".join(lines)
    worksheet.write_text("\n".join(ln.rstrip() for ln in text.splitlines()).rstrip("\n") + "\n")


def read(path: Path) -> list[Item]:
    return [Item(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def report(items: list[Item]) -> dict:
    """Agreement per axis, and the direction of every disagreement.

    Returns `{"calibrated": False}` and no rate at all when nothing is scored.
    A number nobody produced is worse than an absent one, because it looks the
    same as a number somebody did.
    """
    scored = [i for i in items if i.scored()]
    if not scored:
        return {
            "calibrated": False,
            "scored": 0,
            "selected": len(items),
            "note": (
                "No item has been hand-scored. The judge is uncalibrated and no agreement "
                "rate is quoted -- see `calibration.py` and the Day 8 plan, Phase 4."
            ),
        }

    out: dict = {
        "calibrated": True,
        "scored": len(scored),
        "selected": len(items),
        "contested_scored": sum(i.contested for i in scored),
        "sample_note": (
            "Selection is biased toward contested rows, so this is a lower bound on "
            "agreement rather than a representative rate."
        ),
        "axes": {},
    }
    for axis in AXES:
        agree = sum(1 for i in scored if i.human[axis] == i.judge[axis])
        harsh = sum(1 for i in scored if i.human[axis] and not i.judge[axis])
        lenient = sum(1 for i in scored if not i.human[axis] and i.judge[axis])
        out["axes"][axis] = {
            "n": len(scored),
            "agree": agree,
            "rate": round(agree / len(scored), 4),
            "judge_harsher": harsh,
            "judge_more_lenient": lenient,
        }
    out["all_three_agree"] = sum(1 for i in scored if all(i.human[a] == i.judge[a] for a in AXES))
    return out
