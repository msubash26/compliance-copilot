"""The judge's bookkeeping and the calibration boundary, without a model.

Nothing here asks whether the judge is *right* -- that is what
`golden/judge_calibration/` is for, and it needs a human. What is asserted here is
the machinery around it: that the three axes stay separate, that an unparseable
reply is an error rather than three silent `false`s, that abstentions are skipped
rather than scored, and -- the one that matters most -- that an unscored
calibration file reports "uncalibrated" and quotes no number.
"""

from __future__ import annotations

import json

from regops_evals.agentjudge import (
    AXES,
    Calibration,
    Verdict,
    _extract_json,
    agreement,
    summarise,
)
from regops_evals.calibration import Item, read, report, select, write


def v(task="t-001", arm="supervisor", **kw) -> Verdict:
    return Verdict(task_id=task, arm=arm, seconds=3.6, **kw)


class TestVerdicts:
    def test_the_three_axes_are_reported_separately(self):
        s = summarise([v(supported=True, complete=False, cited_correctly=True)])
        assert s["axes"]["supported"]["passed"] == 1
        assert s["axes"]["complete"]["passed"] == 0
        assert s["axes"]["cited_correctly"]["passed"] == 1
        assert s["all_three"]["passed"] == 0

    def test_an_errored_verdict_is_excluded_rather_than_counted_as_a_failure(self):
        """Three silent `false`s from a dead endpoint would read as a quality regression."""
        s = summarise([v(supported=True, complete=True, cited_correctly=True), v(error="boom")])
        assert s["judged"] == 1 and s["errors"] == 1
        assert s["axes"]["supported"] == {"passed": 1, "n": 1, "rate": 1.0}

    def test_no_verdicts_produces_no_rates_rather_than_zeroes(self):
        s = summarise([])
        assert s["judged"] == 0
        assert all(s["axes"][a]["rate"] is None for a in AXES)

    def test_the_cost_is_reported_because_research_measured_it(self):
        s = summarise([v(supported=True), v(supported=True)])
        assert s["seconds_per_call"] == 3.6


class TestReplyParsing:
    def test_a_bare_object_parses(self):
        assert _extract_json('{"supported": true}') == {"supported": True}

    def test_an_object_wrapped_in_prose_parses(self):
        assert _extract_json('Here you go:\n{"supported": false}\nHope that helps') == {
            "supported": False
        }

    def test_nothing_json_shaped_is_none_not_an_empty_dict(self):
        """`{}` would silently become three `false`s; `None` becomes a recorded error."""
        assert _extract_json("I think it is fine.") is None
        assert _extract_json("") is None


class TestAgreement:
    def test_it_reports_the_direction_of_every_disagreement(self):
        pairs = [
            Calibration("t-1", "supervisor", {"supported": True}, {"supported": False}),
            Calibration("t-2", "supervisor", {"supported": False}, {"supported": True}),
            Calibration("t-3", "supervisor", {"supported": True}, {"supported": True}),
        ]
        a = agreement(pairs)["axes"]["supported"]
        assert a == {
            "n": 3,
            "agree": 1,
            "rate": round(1 / 3, 4),
            "judge_harsher": 1,
            "judge_more_lenient": 1,
        }


# -- the calibration artifact ------------------------------------------------


def _report(**kw) -> dict:
    """A minimal eval artifact: two rows, one of which the judge and the checks
    disagree about."""
    rows = [
        {
            "task_id": "t-001",
            "question": "q1?",
            "answer": "a1",
            "cited_uids": ["aaa:1.1"],
            "gold_uids": ["aaa:1.1"],
            "success": True,
            "retrieved_gold": True,
            "cited_resolvable": True,
            "abstained_correctly": True,
        },
        {
            "task_id": "t-002",
            "question": "q2?",
            "answer": "a2",
            "cited_uids": ["bbb:2.2"],
            "gold_uids": ["bbb:2.2"],
            "success": True,
            "retrieved_gold": True,
            "cited_resolvable": True,
            "abstained_correctly": True,
        },
    ]
    verdicts = [
        {
            "task_id": "t-001",
            "arm": "supervisor",
            "supported": True,
            "complete": True,
            "cited_correctly": True,
            "why": "fine",
            "error": "",
        },
        {
            # Mechanically a success, and the judge refuses it. This is the row a
            # human has something to decide about.
            "task_id": "t-002",
            "arm": "supervisor",
            "supported": False,
            "complete": True,
            "cited_correctly": True,
            "why": "adds a deadline the clause does not state",
            "error": "",
        },
    ]
    return {
        "arms": ["supervisor"],
        "rows": {"supervisor": rows},
        "judge_rows": {"supervisor": verdicts},
    } | kw


class TestSelection:
    def test_contested_rows_come_first(self):
        """Twenty examples everyone already agrees about measure nothing."""
        items = select(_report(), target=2)
        assert [i.task_id for i in items] == ["t-002", "t-001"]
        assert items[0].contested and not items[1].contested

    def test_it_is_deterministic(self):
        assert [i.task_id for i in select(_report())] == [i.task_id for i in select(_report())]

    def test_an_unjudged_row_is_not_offered_for_scoring(self):
        rep = _report()
        rep["judge_rows"]["supervisor"][1]["error"] = "unparseable judge reply"
        assert [i.task_id for i in select(rep)] == ["t-001"]

    def test_the_target_is_a_cap_not_a_quota(self):
        assert len(select(_report(), target=20)) == 2


class TestCalibrationReport:
    def test_an_unscored_file_says_uncalibrated_and_quotes_no_rate(self, tmp_path):
        """Phase 4's honesty rule, asserted rather than promised."""
        items = select(_report())
        rep = report(items)
        assert rep["calibrated"] is False
        assert "axes" not in rep
        assert "uncalibrated" in rep["note"]

    def test_a_partially_scored_file_reports_only_what_was_scored(self):
        items = select(_report())
        items[0].human = {"supported": True, "complete": True, "cited_correctly": True}
        rep = report(items)
        assert rep["calibrated"] is True
        assert rep["scored"] == 1 and rep["selected"] == 2
        # The judge said `supported: false` on this row and the human said true.
        assert rep["axes"]["supported"]["judge_harsher"] == 1
        assert rep["axes"]["supported"]["agree"] == 0

    def test_the_sample_bias_is_stated_in_the_artifact(self):
        items = select(_report())
        items[0].human = dict.fromkeys(AXES, True)
        assert "lower bound" in report(items)["sample_note"]

    def test_it_round_trips_through_the_file(self, tmp_path):
        items = select(_report())
        out = tmp_path / "items.jsonl"
        write(items, out)
        back = read(out)
        assert [i.task_id for i in back] == [i.task_id for i in items]
        assert all(isinstance(i, Item) for i in back)

    def test_the_worksheet_marks_the_contested_rows(self, tmp_path):
        items = select(_report())
        sheet = tmp_path / "worksheet.md"
        write(items, tmp_path / "items.jsonl", worksheet=sheet)
        text = sheet.read_text()
        assert "**contested**" in text
        assert '{"supported": null, "complete": null, "cited_correctly": null}' in text
        assert "ADR-017" in text


def test_a_hand_scored_item_never_carries_a_golden_id_field():
    """ADR-017's boundary, as a shape rather than a promise.

    A calibration item has no route back into `golden/v1`: it names a task and an
    arm, and nothing about it can be merged into a golden record by accident.
    """
    fields = set(json.loads(json.dumps(select(_report())[0].__dict__)))
    assert "golden_id" not in fields and "verification" not in fields
