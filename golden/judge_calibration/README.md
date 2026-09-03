# `golden/judge_calibration` — the only human scores in this project

Twenty judge verdicts selected for a person to score by hand, so that Day 8 can
state an agreement rate instead of asserting that its LLM judge is trustworthy.

**This is a separate artifact and it stays separate.** `golden/v1` carries
`verification.human_reviewed: false` on all 150 items, and
`evals/tests/test_golden_set.py` asserts it, because ADR-017 draws an explicit
line around what a machine-built set may claim. Scores here are **never merged
into `golden/v1` and never used to relabel a golden item.** What they license is
one sentence — *"the judge agrees with a human N of 20, and here is where it does
not"* — and a calibration item has no `golden_id` field, so there is no route back
into the golden set even by accident.

## Files

| file | what it is |
|---|---|
| `items.jsonl` | the selected verdicts, machine-readable, with a blank `human` object |
| `worksheet.md` | the same items with their cited clauses inlined, for reading |
| `agreement.json` | the report, or `{"calibrated": false}` if nothing is scored |

## How to score

```
uv run regops-evals calibrate --eval results/day8/eval.json     # writes both files
# read worksheet.md, score each item, copy the three booleans into items.jsonl
uv run regops-evals calibration-report
```

Three axes, scored independently — a composite hides which one failed, and they
fail for different reasons:

- **`supported`** — is every factual claim in the answer stated in the clauses it
  cited? A claim that adds a threshold or a deadline the clauses do not state is
  not supported, *even if it is true in reality*.
- **`complete`** — does the answer cover what the gold clauses state? An answer can
  be perfectly supported and answer a third of the question.
- **`cited_correctly`** — are the cited clauses the ones the support actually came
  from? Layer 2 proves an identifier resolves; only a reader can tell whether it is
  the right clause. This is the axis no mechanical check can see, and the one a
  compliance reviewer would care about most.

Score before reading the judge's `why`. It is in the file because the
disagreements are the point, and it is an anchor if read first.

## The sample is biased on purpose

Selection puts **contested** rows first — the ones where the judge and the
mechanical outcomes reach opposite verdicts. Twenty examples everyone already
agrees about would report a high agreement rate that is an artifact of picking
easy cases.

So this is **not a representative sample**, and the agreement rate it produces is a
**lower bound**. That is the useful direction to be wrong in, and
`agreement.json` says so in its own `sample_note` rather than leaving it to a
reader to work out.

## If it is not scored

`calibration-report` prints `{"calibrated": false}` and **quotes no number**, and
the Day 8 write-up says the judge is uncalibrated. That was decided before the
work started. An estimated agreement rate looks exactly like a measured one, which
is the whole problem with estimating it.
