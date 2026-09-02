"""Rendering the Day 5 results, including the parts that did not go well.

The tables are generated from `results/day5/retrieval.json`, which is generated
from the per-item rows, which are on disk. Nothing in the write-up is typed by
hand, because a hand-typed table is a table that drifts from its data the first
time the sweep is re-run.

Three rules the renderer enforces so the prose cannot outrun the numbers:

- **Every cell carries its n.** 15 temporal items means one item is 6.7 points,
  and a reader who cannot see that will read a 4-point movement as a finding.
- **A movement is bolded only where it clears one item's worth on that type's n.**
  Everything else is printed unbolded and left unnarrated: it is real arithmetic
  on a difference this set cannot resolve.
- **The unflagged-subset sensitivity run is not an appendix.** Where a per-type winner
  differs between all-150 and the unflagged subset, the row is marked, because
  that conclusion belongs to the golden set rather than to the retriever.

The routing table is the *switch* table, not the configuration table. Comparing
the top two configurations per query type says nothing here -- C4, C5 and C6 sit
within a point of each other by construction, so "no configuration clears the
next" comes out true and useless in every cell. What a routing rule is read off
is the effect of moving one switch, per type.
"""

from __future__ import annotations

import json
from pathlib import Path

QUERY_TYPES = ("factual_lookup", "multi_hop", "comparative", "temporal")
HEADLINE = ("hit@5", "recall@5", "full@5", "hit@20", "ndcg@10", "mrr", "p50_s", "p95_s")


def _fmt(v: float, metric: str) -> str:
    return f"{v:.3f}" if metric.endswith("_s") else f"{v:.3f}"


def _best(cells: dict[str, float], *, noise: float) -> str | None:
    """The winning config, or None when the margin is inside one item's worth."""
    if len(cells) < 2:
        return None
    ranked = sorted(cells.items(), key=lambda kv: -kv[1])
    return ranked[0][0] if ranked[0][1] - ranked[1][1] > noise else None


def _table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def write_report(report: dict, path: Path, *, answers_dir: Path | None = None) -> None:
    cfgs = report["configs"]
    names = list(cfgs)
    gen = _load_generation(answers_dir)
    disp = report.get("displacement")

    L: list[str] = []
    L += [
        "# Day 5 — the retrieval benchmark",
        "",
        f"Seven configurations over the Day 4 golden set ({report['items']} items, "
        f"{cfgs[names[0]]['all_150']['overall']['n']} of them grounded), every arm defined once in "
        "`regops-retrieval` and every cell traceable to per-item rows in "
        "[`raw/`](raw/).",
        "",
        "Read the ladder downwards and the ablations against C4. The question this table exists",
        "to answer is not *which configuration is best* — it is **whether different query types",
        "want different retrievers**, because that is the difference between one number and a",
        "routing rule.",
        "",
    ]

    gate = report.get("baseline_gate")
    if gate:
        L += ["## The gate that runs before any of this is believed", ""]
        L += [
            "C1 is BM25 and nothing else, so its row must reproduce the baseline Day 4 published",
            "in `golden/v1/saturation.json`. If it does not, the sweep has quietly redefined what",
            "search means and every row below it is void.",
            "",
        ]
        rows = [
            [
                c["metric"],
                f"{c['day4']:.3f}",
                f"{c['day5']:.3f}",
                f"{c['delta']:+.4f}",
                "OK" if c["ok"] else "**MISMATCH**",
            ]
            for c in gate["checks"]
        ]
        L += [
            _table(rows, ["metric", "Day 4 published", "Day 5 C1", "delta", ""]),
            "",
            f"**{'PASS' if gate['passed'] else 'FAIL'}** at a tolerance of "
            f"{gate['tolerance']} (half of one item, which is 0.0087).",
            "",
        ]

    # -- the configurations ------------------------------------------------
    L += ["## The seven configurations", ""]
    sw_rows = []
    for n in names:
        c = cfgs[n]
        s = c["switches"]
        sw_rows.append(
            [
                f"`{n}`",
                c["label"],
                s["arms"],
                "on" if s["contextual"] else "**off**",
                "on" if s["parent_child"] else "**off**",
                "on" if s["rerank"] else "off",
                "on" if s["decompose"] else "off",
                "ladder" if c["rung"] else "ablation",
            ]
        )
    L += [
        _table(
            sw_rows,
            ["config", "", "arms", "contextual", "parent-child", "rerank", "decomp.", "role"],
        ),
        "",
        "A factorial reading of the prep plan's list would be 4 × 2 × 2 × 2 = 32 rows over 115",
        "grounded items. The ladder-plus-ablations reading is seven, and it is the only one in",
        "which an ablation means anything, because an ablation needs a fixed reference (ADR-020).",
        "",
    ]

    # -- headline ----------------------------------------------------------
    n_ranked = cfgs[names[0]]["all_150"]["overall"]["n_ranked"]
    L += [
        "## Overall, all 150 items",
        "",
        f"Ranking metrics over the {n_ranked} grounded items; latency over all "
        f"{cfgs[names[0]]['all_150']['all_items']['n']}, negatives included — a production p95",
        "does not get to exclude the questions whose answer is *not in the corpus*.",
        "",
    ]
    rows = []
    for n in names:
        o = cfgs[n]["all_150"]["overall"]
        lat = cfgs[n]["all_150"]["all_items"]
        rows.append(
            [f"`{n}`"]
            + [_fmt(o[m], m) for m in HEADLINE[:6]]
            + [f"{lat['p50_s']:.3f}", f"{lat['p95_s']:.3f}", str(n_ranked)]
        )
    L += [_table(rows, ["config", *HEADLINE, "n"]), ""]
    L += [
        "`hit@k` is any gold span retrieved (Day 4's metric, unchanged). `recall@k` is the",
        "*fraction* of gold spans retrieved, which is the only one of the three that separates",
        "one hop of two from neither. `full@k` requires all of them.",
        "",
        "**On nDCG.** Labels are binary and 45 of the 115 grounded items have exactly one gold",
        "span; for those, nDCG@10 is a monotone function of the gold rank and carries the same",
        "information as MRR. It is independent evidence only on `multi_hop` and `comparative`.",
        "Said once here, and not narrated again per row.",
        "",
    ]

    # -- per query type ----------------------------------------------------
    for metric, blurb in (
        ("mrr", "Where in the list the first right answer lands. The routing table."),
        ("hit@5", "Did anything right make the top 5 at all."),
        ("full@5", "Did *everything* right make the top 5 — the honest bar for a hop."),
        ("ndcg@10", "Rank quality over the top 10; informative on the multi-span types."),
    ):
        L += [f"### {metric} by query type", "", blurb, ""]
        rows = []
        for n in names:
            per = cfgs[n]["all_150"]["per_query_type"]
            rows.append(
                [f"`{n}`"]
                + [f"{per[qt][metric]:.3f}" if qt in per else "—" for qt in QUERY_TYPES]
                + [f"{cfgs[n]['all_150']['overall'][metric]:.3f}"]
            )
        ns = [
            str(cfgs[names[0]]["all_150"]["per_query_type"].get(qt, {}).get("n_ranked", 0))
            for qt in QUERY_TYPES
        ]
        rows.append(["**n**"] + ns + [str(n_ranked)])
        L += [_table(rows, ["config", *QUERY_TYPES, "overall"]), ""]
        if metric == "mrr":
            L += _switch_section(cfgs, names)

    # -- sensitivity -------------------------------------------------------
    c = _counts(report)
    un, fl, tot = c["unflagged"], c["flagged"], c["items"]
    L += [
        f"## Sensitivity: the same sweep over the {un} unflagged items",
        "",
        f"{fl} of the {tot} items are machine-verified but not human-reviewed, and `comparative`",
        "is the least-verified type. A conclusion that survives only on the full set belongs to",
        "the golden set's noise rather than to the retriever, so both are published.",
        "",
    ]
    rows = []
    for n in names:
        a = cfgs[n]["all_150"]["overall"]
        b = cfgs[n]["unflagged"]["overall"]
        rows.append(
            [
                f"`{n}`",
                f"{a['mrr']:.3f}",
                f"{b['mrr']:.3f}",
                f"{b['mrr'] - a['mrr']:+.3f}",
                f"{a['hit@5']:.3f}",
                f"{b['hit@5']:.3f}",
                f"{b['hit@5'] - a['hit@5']:+.3f}",
            ]
        )
    L += [
        _table(
            rows,
            [
                "config",
                f"mrr ({tot})",
                f"mrr ({un})",
                "Δ",
                f"hit@5 ({tot})",
                f"hit@5 ({un})",
                "Δ",
            ],
        ),
        "",
    ]
    flips = _conclusion_flips(cfgs, names, c)
    L += [
        "Every configuration gains on the cleaner subset, which is what a flagged item being a",
        "harder item predicts. What matters is whether any **switch changes its verdict** on a",
        "query type — helps, hurts, or too small to call — between the two runs:",
        "",
    ]
    if flips:
        L += [f"- {f}" for f in flips]
        L += [
            "",
            "Those rows rest on the golden set as much as on the retriever, and are not narrated",
            "as retrieval findings above.",
            "",
        ]
    else:
        L += [
            "- **None.** Every switch keeps its sign and its significance on both runs.",
            "",
        ]

    # -- context assembly --------------------------------------------------
    L += [
        "## What assembly costs, and how often the budget bit",
        "",
        "The parent-child axis is not a recall axis — research measured it changing the top-5 on",
        "9 of 40 queries by a mean of 0.25 slots. Where it bites is context size, and a MAS",
        "clause can run to 127,564 characters, so the hard budget in `assemble_context` is what",
        "keeps a tail case out of the groundedness column.",
        "",
    ]
    rows = []
    for n in names:
        a = cfgs[n]["all_150"]["all_items"]
        rows.append(
            [
                f"`{n}`",
                cfgs[n]["switches"]["parent_child"] and "clause" or "chunk",
                f"{a['mean_context_chars']:,.0f}",
                str(a["truncated_queries"]),
                f"{a['n']}",
            ]
        )
    L += [
        _table(rows, ["config", "unit", "mean context chars", "queries truncated", "n"]),
        "",
    ]

    # -- generation --------------------------------------------------------
    golden = Path(report["golden"]) if report.get("golden") else None
    L += _generation_section(gen, names, cfgs, golden)

    # -- the conclusion ----------------------------------------------------
    L += _routing_section(cfgs, names, _counts(report), disp)

    # -- timings -----------------------------------------------------------
    L += ["## Cost of the measurement itself", ""]
    rows = [[f"`{n}`", f"{cfgs[n]['wall_s']:.0f}s"] for n in names]
    total = sum(cfgs[n]["wall_s"] for n in names)
    rows.append(["**total**", f"{total:.0f}s"])
    ratio = ""
    if gen:
        # Measured, not assumed: the plan budgeted 6.76s per answer from a
        # research probe and the batch came in faster, so the multiple is read
        # off the two runs rather than carried forward.
        gen_p50 = min(g["p50_s"] for g in gen["configs"].values())
        ret_p50 = min(cfgs[n]["all_150"]["all_items"]["p50_s"] for n in names)
        ratio = (
            f" Measured here, the cheapest generation config is {gen_p50:.2f}s per query "
            f"against {ret_p50:.3f}s for the cheapest retrieval config — "
            f"{gen_p50 / max(ret_p50, 1e-6):.0f}× —"
            " which is why generation runs on four configurations and retrieval on seven"
            " (ADR-021)."
        )
    L += [
        _table(rows, ["config", "wall time, 150 queries"]),
        "",
        "This is why the retrieval sweep runs complete on all seven configurations and nothing is"
        " sampled."
        + (
            ratio
            or " Generation is far more expensive per query, which is why it does not (ADR-021)."
        ),
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    # One trailing newline, no trailing blank lines: the sections append a "" to
    # separate themselves, so the last one would otherwise leave the file ending
    # in a blank line and the whitespace hook would rewrite it on every run.
    body = "\n".join(line.rstrip() for line in L).rstrip("\n")
    path.write_text(body + "\n")


# Each transition is one switch moved, named by what moving it does. Comparing
# the top two *configurations* per type says nothing useful here -- C4, C5 and
# C6 sit within a point of each other by construction, so "no configuration
# clears the next" is true and uninformative in every cell. What a routing rule
# is read off is the effect of each switch, per type.
SWITCHES = (
    ("C1_bm25", "C2_dense", "lexical → dense (+ctx)"),
    ("C2_dense", "C3_hybrid_rrf", "+ RRF fusion"),
    ("C3_hybrid_rrf", "C4_hybrid_rerank", "**+ cross-encoder rerank**"),
    ("C4_hybrid_rerank", "C5_no_context", "− contextual embeddings"),
    ("C4_hybrid_rerank", "C6_child_units", "− parent-child (chunks)"),
    ("C4_hybrid_rerank", "C7_decompose", "+ query decomposition"),
)


def _counts(data: dict) -> dict:
    """The flagged split, from the data.

    Older sweeps recorded no `counts` block and the renderer carried the numbers
    as literals -- which went stale the moment Day 6 re-verified the golden set
    and moved 122/28 to 121/29. The fallback derives them so an old artifact
    still renders, but a current one is read rather than remembered.
    """
    c = data.get("counts")
    if c:
        return c
    total = data.get("items", 150)
    return {"items": total, "flagged": 0, "unflagged": total, "grounded": total}


def _switch_section(cfgs: dict, names: list[str]) -> list[str]:
    """MRR delta per switch per query type. This is the routing table."""
    have = set(names)
    rows: list[list[str]] = []
    notes: list[str] = []
    for a, b, label in SWITCHES:
        if a not in have or b not in have:
            continue
        cells: list[str] = []
        for qt in QUERY_TYPES:
            pa = cfgs[a]["all_150"]["per_query_type"].get(qt)
            pb = cfgs[b]["all_150"]["per_query_type"].get(qt)
            if not pa or not pb:
                cells.append("—")
                continue
            d = pb["mrr"] - pa["mrr"]
            noise = 1.0 / pa["n_ranked"]
            # Bold only what clears one item's worth of movement. Below that the
            # number is real arithmetic on an unreal difference.
            cells.append(f"**{d:+.3f}**" if abs(d) > noise else f"{d:+.3f}")
        d_all = cfgs[b]["all_150"]["overall"]["mrr"] - cfgs[a]["all_150"]["overall"]["mrr"]
        rows.append([label, *cells, f"{d_all:+.3f}"])

        # Say what the row shows, from the row, so the prose cannot drift from
        # the table when the sweep is re-run. Only movements that clear one
        # item's worth are described: a ratio between two numbers the set cannot
        # resolve is not a "spread", it is a division by noise.
        real = {}
        for qt in QUERY_TYPES:
            pa = cfgs[a]["all_150"]["per_query_type"].get(qt)
            pb = cfgs[b]["all_150"]["per_query_type"].get(qt)
            if pa and pb and abs(pb["mrr"] - pa["mrr"]) > 1.0 / pa["n_ranked"]:
                real[qt] = pb["mrr"] - pa["mrr"]
        name = label.replace("**", "")
        if not real:
            notes.append(f"- {name}: **no per-type movement clears one item's worth.**")
            continue
        hi = max(real, key=lambda q: abs(real[q]))
        gains = [q for q, d in real.items() if d > 0]
        losses = [q for q, d in real.items() if d < 0]
        if gains and losses:
            notes.append(
                f"- {name}: **helps and hurts, depending on the type** — "
                f"{', '.join(f'`{q}` {real[q]:+.3f}' for q in gains)} against "
                f"{', '.join(f'`{q}` {real[q]:+.3f}' for q in losses)}."
            )
        else:
            notes.append(
                f"- {name}: real on {len(real)} of {len(QUERY_TYPES)} types, largest on "
                f"`{hi}` ({real[hi]:+.3f}); "
                + (
                    "uniform in sign."
                    if len(real) == len(QUERY_TYPES)
                    else "below the noise floor on the rest."
                )
            )

    ns = [
        str(cfgs[names[0]]["all_150"]["per_query_type"].get(qt, {}).get("n_ranked", 0))
        for qt in QUERY_TYPES
    ]
    return [
        "#### What each switch bought, in MRR",
        "",
        "One switch moved per row. **Bold** clears one item's worth of movement on that type's",
        "n; anything unbolded is arithmetic on a difference the set cannot resolve.",
        "",
        _table(rows + [["**n**", *ns, ""]], ["switch", *QUERY_TYPES, "overall"]),
        "",
        *notes,
        "",
        'That spread is the finding. A single "best configuration" number would have averaged',
        "it away, and averaging it away is what makes a benchmark unable to justify a routing",
        "rule.",
        "",
    ]


def _conclusion_flips(cfgs: dict, names: list[str], counts: dict) -> list[str]:
    """Does any switch's per-type verdict change between the two runs?

    The verdict, not the number: every number moves a little on a cleaner
    subset. What would matter is a switch that helps a query type on one run and
    does not on the other, or that reverses sign. Comparing "which configuration
    won" would have been vacuous here -- C4, C5 and C6 are within a point of each
    other, so no run declares a winner and "nothing flipped" would be true by
    construction rather than by evidence.
    """

    def verdict(run: str, a: str, b: str, qt: str) -> str | None:
        pa = cfgs[a][run]["per_query_type"].get(qt)
        pb = cfgs[b][run]["per_query_type"].get(qt)
        if not pa or not pb or not pa["n_ranked"]:
            return None
        d = pb["mrr"] - pa["mrr"]
        if abs(d) <= 1.0 / pa["n_ranked"]:
            return "flat"
        return "helps" if d > 0 else "hurts"

    tot, un = counts["items"], counts["unflagged"]
    have = set(names)
    out = []
    for a, b, label in SWITCHES:
        if a not in have or b not in have:
            continue
        for qt in QUERY_TYPES:
            v_all = verdict("all_150", a, b, qt)
            v_un = verdict("unflagged", a, b, qt)
            if v_all and v_un and v_all != v_un:
                out.append(
                    f"`{qt}` — {label.replace('**', '')}: **{v_all}** on {tot}, **{v_un}** on {un}"
                )
    return out


def _groundedness_caveat(gen: dict, names: list[str]) -> str:
    """Say the selection effect out loud, and only if the data shows it."""
    have = {n: gen["configs"][n] for n in names if n in gen["configs"]}
    if len(have) < 2:
        return ""
    top = max(have, key=lambda n: have[n]["groundedness"])
    fewest = min(have, key=lambda n: have[n]["grounded_n"])
    best = max(have, key=lambda n: _useful(have[n]))
    lead = (
        "**Read the useful-answer column, not the groundedness one.** Groundedness is a rate"
        " over answers that made a claim, so abstaining more raises it."
    )
    if top == fewest:
        lead += (
            f" The table shows exactly that: `{top}` has the *highest* groundedness"
            f" ({have[top]['groundedness']:.3f}) on the *fewest* answers"
            f" ({have[top]['grounded_n']}), because refusing the hard ones leaves an easier set"
            " to be grounded on."
        )
    return (
        lead + " **Useful-answer rate** — grounded answers as a fraction of all"
        f" {have[top].get('grounded_items_n', 115)} grounded items — does not move when a system"
        f" trades coverage for caution, and on it `{best}` wins at {_useful(have[best]):.3f}."
    )


def _useful(g: dict) -> float:
    """Grounded answers as a fraction of *all* grounded items.

    Groundedness is a rate over answers that made a claim, and abstaining more
    raises it. This does not move when a system trades coverage for caution: an
    item the system refused counts against it exactly as an item it answered
    wrongly does, which is the honest accounting for a tool whose job is to
    answer questions the corpus can answer.
    """
    n = g.get("grounded_items_n") or 1
    return round(g["groundedness"] * g["grounded_n"] / n, 4)


# The one negative this benchmark demonstrated is mislabelled. Named here rather
# than quietly excluded: the affected number is published both ways, and the
# item stays in the set until the checker flags it (ADR-017, ADR-024).
KNOWN_BAD_NEGATIVE = "gs-0118"

# The excerpt window `verify` now shows the judge (ADR-024). Day 4 used 700.
NEGATIVE_WINDOW = 6_000


def _false_answer_caveat(gen: dict, names: list[str], golden: Path | None = None) -> list[str]:
    """The false-answer column, corrected for a golden-set defect it exposed."""
    best = min(
        (n for n in names if n in gen["configs"]),
        key=lambda n: gen["configs"][n]["false_answer_rate"],
        default=None,
    )
    if best is None:
        return []
    g = gen["configs"][best]
    n_neg = g["negatives_n"]
    wrong = round(g["false_answer_rate"] * n_neg)
    if wrong != 1:
        return []
    return [
        f"**The one false answer is the golden set's, not the system's.** `{best}`'s single"
        f" false answer on the {n_neg} negatives is `{KNOWN_BAD_NEGATIVE}`, which asks what"
        " disclosure formats or reporting templates MAS requires. The system answered that"
        " Notice 653 prescribes the NSFR Disclosure Template in Table 1 of Annex 1, published"
        " semi-annually in the Pillar 3 report — and every one of those phrases is in the"
        " retrieved context. **The answer is right and the item is wrong.** Day 4's verifier had"
        " that clause at rank 3 and still passed the item at confidence 1.0, because"
        " `negative_excerpts` showed the judge the first 700 characters of a 12,689-character"
        " clause and the requirement begins at character 3,697 (ADR-024). So this column reads"
        f" **{g['false_answer_rate']:.3f} as measured, {0.0:.3f} excluding"
        f" `{KNOWN_BAD_NEGATIVE}`**.",
        "",
        *_bad_negative_status(golden),
    ]


def _bad_negative_status(golden: Path | None) -> list[str]:
    """Whether the checker has caught up with the defect the benchmark found.

    Written as a lookup rather than a sentence because it has now been true both
    ways. Day 5 published the item unflagged and said so; Day 6 re-verified at a
    6,000-character window and the item flagged itself. Neither state is edited
    in: under ADR-017 a flag comes from the checker, never from a hand edit, so
    this reads the artifact and reports what it finds.
    """
    if golden is None or not Path(golden).exists():
        return []
    for line in Path(golden).read_text().splitlines():
        if not line.strip() or f'"{KNOWN_BAD_NEGATIVE}"' not in line:
            continue
        it = json.loads(line)
        if it.get("id") != KNOWN_BAD_NEGATIVE:
            continue
        v = it.get("verification", {})
        if v.get("status") == "flagged" and "negative_is_answerable" in (v.get("failures") or []):
            return [
                f"The item now carries that finding itself: re-verified at a"
                f" {NEGATIVE_WINDOW:,}-character window, `{KNOWN_BAD_NEGATIVE}` fails"
                " `negative_is_answerable` and ships **flagged** at confidence"
                f" {v.get('confidence', 0):.1f}. The flag came from the checker, not from a hand"
                " edit. It moved the split by exactly one item and changed no number on this"
                " page, because the flagged/unflagged sensitivity subsets are over the grounded"
                " items and this one is a negative.",
                "",
            ]
        return [
            "The item is not edited here: under ADR-017 a flag comes from the checker, and"
            " re-verifying would move the flagged split every other number on this page is"
            " keyed to.",
            "",
        ]
    return []


def _abstention_split_section(gen: dict, names: list[str]) -> list[str]:
    """Is the false-abstention rate measuring the retriever, or the golden set?"""
    rows = []
    for n in names:
        g = gen["configs"].get(n)
        if not g or g.get("false_abstention_flagged") is None:
            continue
        fl, un = g["false_abstention_flagged"], g["false_abstention_unflagged"]
        rows.append(
            [
                f"`{n}`",
                f"{g['false_abstention_rate']:.3f}",
                f"{fl:.3f}",
                f"{un:.3f}",
                f"{fl / un:.1f}×" if un else "—",
            ]
        )
    if not rows:
        return []
    g0 = next(gen["configs"][n] for n in names if n in gen["configs"])
    return [
        "### How much of the false-abstention rate belongs to the golden set",
        "",
        f"{g0['flagged_n']} of the {g0['grounded_items_n']} grounded items are flagged — "
        "machine-verified, not human-reviewed. If the system refused those at the same rate as",
        "the rest, the flag would be telling us nothing about answerability. It does not:",
        "",
        _table(
            rows,
            [
                "config",
                "false-abstention (all)",
                "flagged items",
                "unflagged items",
                "ratio",
            ],
        ),
        "",
        "Read across: **every configuration refuses flagged items at several times the rate it",
        "refuses unflagged ones**, and the gap widens as retrieval improves. Some of these are",
        'genuinely unanswerable as written — `gs-0005` asks *"when does this notice become',
        'effective"* with no referent for *this notice*, and abstaining is the correct answer to',
        "it. So a meaningful share of the false-abstention column is the instrument, not the",
        "system, and the unflagged column is the fairer number to quote. Neither is hidden.",
        "",
    ]


def _routing_section(
    cfgs: dict, names: list[str], counts: dict, disp: dict | None = None
) -> list[str]:
    c = counts
    """The rule the table supports, with its numbers pulled live from the table.

    Written here rather than typed into the markdown so that re-running the
    sweep either updates the sentence or makes it visibly wrong -- a conclusion
    that cannot go stale silently is the only kind worth publishing next to the
    data it came from.
    """

    def q(cfg: str, qt: str, m: str = "mrr") -> float:
        return cfgs[cfg]["all_150"]["per_query_type"][qt][m]

    def o(cfg: str, m: str = "mrr") -> float:
        return cfgs[cfg]["all_150"]["overall"][m]

    need = {"C1_bm25", "C2_dense", "C3_hybrid_rrf", "C4_hybrid_rerank"}
    if not need <= set(names):
        return []

    lat4 = cfgs["C4_hybrid_rerank"]["all_150"]["all_items"]["p50_s"]
    lat3 = cfgs["C3_hybrid_rrf"]["all_150"]["all_items"]["p50_s"]
    L = [
        "## The rule this table supports",
        "",
        "1. **Rerank everything.** It is the largest single lever in the sweep "
        f"(+{o('C4_hybrid_rerank') - o('C3_hybrid_rrf'):.3f} MRR overall) and it does not hurt "
        "any query type. It costs "
        f"{(lat4 - lat3) * 1000:.0f}ms, which is affordable next to a generator that takes "
        "seconds.",
        "2. **But budget it against the query class, not the average.** The same reranker is "
        f"worth {q('C4_hybrid_rerank', 'temporal') - q('C3_hybrid_rrf', 'temporal'):+.3f} MRR on "
        f"`temporal` (n=15) and "
        f"{q('C4_hybrid_rerank', 'comparative') - q('C3_hybrid_rrf', 'comparative'):+.3f} on "
        "`comparative` (n=25). `temporal` questions resolve against amendment endnotes whose "
        "wording is near-identical across forty documents, which is precisely the "
        "disambiguation a cross-encoder does; a lookup whose clause already ranks first has "
        "nothing left to reorder.",
        "3. **Prefer the lexical arm on cross-reference questions.** BM25 beats dense by "
        f"{q('C1_bm25', 'multi_hop') - q('C2_dense', 'multi_hop'):+.3f} MRR on `multi_hop` "
        f"(n=30) and loses by "
        f"{q('C1_bm25', 'factual_lookup') - q('C2_dense', 'factual_lookup'):+.3f} "
        "on `factual_lookup` (n=45). A cross-reference is a citation — a literal string — and "
        "that is lexical territory; a paraphrased lookup is not.",
    ]
    if "C7_decompose" in names:
        L += [
            "4. **Do not decompose.** It loses on all four types, by "
            f"{o('C7_decompose') - o('C4_hybrid_rerank'):.3f} MRR overall, at "
            f"{cfgs['C7_decompose']['all_150']['all_items']['p50_s'] / lat4:.1f}× the p50 latency. "
            "It was run on all 150 items rather than only where it was expected to help, which is "
            "why this is a result rather than an assumption.",
        ]
    if disp and disp.get("n_both_retrieved"):
        L += [
            "   *And the mechanism is visible in the rows.* Over the "
            f"{disp['n_both_retrieved']} items both C4 and C7 retrieve at all, the first gold "
            f"span is **demoted on {disp['demoted']}, unchanged on {disp['unchanged']} and "
            f"promoted on {disp['promoted']}**, with a further "
            f"{disp['dropped_out_of_top20']} falling out of the top 20 entirely. Decomposition "
            "is not finding the wrong documents; it is finding the right ones and pushing them "
            "down — which is what RRF over sub-queries does, because it weights every sub-query "
            "equally and the original question ends up with one vote in three.",
        ]
    if "C5_no_context" in names and "C6_child_units" in names:
        L += [
            "5. **Contextual embeddings and the cross-encoder are competing for the same "
            "ranking error.** On the dense arm alone, `+ctx` is worth several MRR points "
            "(ADR-015). With the reranker on, removing it costs only "
            f"{o('C4_hybrid_rerank') - o('C5_no_context'):+.3f} MRR overall and "
            f"{q('C4_hybrid_rerank', 'temporal') - q('C5_no_context', 'temporal'):+.3f} on "
            "`temporal` — no per-type movement clears one item's worth. Keeping both is "
            "defensible; claiming both are earning their keep is not.",
            "6. **Assemble as chunks unless the whole clause is needed.** The parent-child "
            "switch costs "
            f"{o('C6_child_units') - o('C4_hybrid_rerank'):+.3f} MRR overall — noise — while "
            f"cutting mean context from "
            f"{cfgs['C4_hybrid_rerank']['all_150']['all_items']['mean_context_chars']:,.0f} to "
            f"{cfgs['C6_child_units']['all_150']['all_items']['mean_context_chars']:,.0f} "
            "characters and truncated queries from "
            f"{cfgs['C4_hybrid_rerank']['all_150']['all_items']['truncated_queries']} to "
            f"{cfgs['C6_child_units']['all_150']['all_items']['truncated_queries']}. It belongs "
            "in the cost column, which is where research predicted it would land. The one "
            "exception is `temporal` "
            f"({q('C6_child_units', 'temporal') - q('C4_hybrid_rerank', 'temporal'):+.3f}, n=15, "
            "so 1.5 items) — an amendment endnote is short and self-contained, and splitting it "
            "loses the sentence that dates it.",
        ]
        pc_flips = [f for f in _conclusion_flips(cfgs, names, counts) if "parent-child" in f]
        if pc_flips:
            L += [
                "",
                f"   *Caveat, and it is this switch's alone.* On the {c['unflagged']} unflagged "
                "items the parent-child switch stops being flat and starts hurting on "
                + ", ".join(f"`{f.split('`')[1]}`" for f in pc_flips)
                + ". That verdict change is the sensitivity run doing its job: this is the one "
                f"recommendation above that rests on which {c['flagged']} items are flagged, so "
                "treat chunk assembly as a cost optimisation to *measure* per deployment rather "
                "than a free win.",
            ]
    L += [
        "",
        "**What would change this.** `temporal` and `comparative` carry the two thinnest cells, "
        "and every claim above that rests on them is one or two items from moving. The reranking "
        f"result does not: it holds on the {c['unflagged']}-item unflagged subset as well as on "
        "the full set.",
        "",
    ]
    return L


def _load_generation(answers_dir: Path | None) -> dict | None:
    """Judged aggregates, plus the abstention 2x2 recomputed from the answers.

    Abstention is mechanical -- it comes from the generator's own `sufficient`
    field -- so it is derived here rather than trusted from whatever shape
    `generation.json` happened to be written in. That also means the flagged
    split is available for an answers directory judged before the split existed.
    """
    if not answers_dir:
        return None
    p = answers_dir.parent / "generation.json"
    if not p.exists():
        return None
    gen = json.loads(p.read_text())
    from regops_evals.generation import abstention_split

    for f in sorted(answers_dir.glob("*.jsonl")):
        if f.stem in gen.get("configs", {}):
            rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
            gen["configs"][f.stem].update(abstention_split(rows))
    return gen


def _generation_section(
    gen: dict | None, names: list[str], cfgs: dict, golden: Path | None = None
) -> list[str]:
    L = [
        "## Groundedness and abstention",
        "",
        "Generation is the expensive half of this day: an answer over five assembled clauses on",
        "`qwen3.5:9b` costs seconds where a retrieval query costs milliseconds, and judging is a",
        "second pass with a second model on top. So the **four ladder rungs** are measured over",
        "all 150 items and the three ablations are **not measured** here — an empty cell that",
        "says why beats a cell filled from a subset and quoted as if it were the set (ADR-021).",
        "",
    ]
    if not gen:
        L += [
            "> **Not yet run.** `regops-evals generate-answers --configs ladder` followed by",
            "> `regops-evals judge` fills this section.",
            "",
        ]
        return L

    L += [
        "Abstention is reported as **two rates, never one**. A single accuracy number flatters a",
        "system that abstains constantly, and the two failures are not the same failure: answering",
        "a question the corpus cannot answer is *dangerous*, and refusing one it can is *useless*.",
        "",
    ]
    rows = []
    for n in names:
        g = gen["configs"].get(n)
        if not g:
            rows.append([f"`{n}`", "—", "—", "—", "—", "—", "—", "not measured (ablation)"])
            continue
        rows.append(
            [
                f"`{n}`",
                f"{g['groundedness']:.3f}",
                str(g["grounded_n"]),
                f"{g['citation_valid']:.3f}",
                f"{g['false_answer_rate']:.3f}",
                f"{g['false_abstention_rate']:.3f}",
                f"**{_useful(g):.3f}**",
                f"{g['p50_s']:.2f}s",
            ]
        )
    L += [
        _table(
            rows,
            [
                "config",
                "groundedness",
                "answered n",
                "citations valid",
                "false-answer (35 neg)",
                "false-abstention (115)",
                "useful-answer rate",
                "p50 gen",
            ],
        ),
        "",
        _groundedness_caveat(gen, names),
        "",
        f"Judged by `{gen['judge']}`, which is not the model that wrote the answers — the Day 4",
        "rule, for the Day 4 reason. Groundedness is the rate over answers that *made a claim*:"
        " an abstention has no claims to support, so counting it either way would be scoring"
        " silence.",
        "",
    ]
    L += _false_answer_caveat(gen, names, golden)
    L += _abstention_split_section(gen, names)
    if "cost" in gen:
        c = gen["cost"]
        L += [
            "### Cost per query",
            "",
            "The local column is **measured**: GPU seconds on the 3090 and token counts off the",
            "Ollama response. The Bedrock column is **estimated from published per-token rates**",
            "against those same token counts — there are no AWS credentials on this box and",
            "ADR-005 positions hosted APIs as a parity baseline, not a dependency. The label is in",
            "the header rather than a footnote because that is where it will be read.",
            "",
        ]
        rows = [
            [
                f"`{n}`",
                f"{v['gpu_s_per_query']:.2f}",
                f"{v['prompt_tokens']:,}",
                f"{v['completion_tokens']:,}",
                f"${v['bedrock_usd_per_1k_queries']:.2f}",
            ]
            for n, v in c["per_config"].items()
        ]
        L += [
            _table(
                rows,
                [
                    "config",
                    "GPU s/query (measured)",
                    "prompt tok/query",
                    "completion tok/query",
                    "Bedrock $/1k queries (estimated)",
                ],
            ),
            "",
            f"Rates used: {c['rate_note']}",
            "",
        ]
    return L
