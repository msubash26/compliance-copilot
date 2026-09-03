"""One budget, three currencies, and the reducer a fan-out needs.

No model and no database. Everything here is arithmetic and the shape of a
state update, which is exactly the part that has to be right before five workers
start writing to it concurrently.
"""

from __future__ import annotations

import pytest
from regops_agents.budget import (
    STEP_CEILING,
    TOKEN_CEILING,
    WALL_CLOCK,
    Budget,
    merge_spend,
    new_spend,
    spent,
    summary,
    tokens,
    usd,
)


def test_a_fresh_spend_is_zero_in_every_currency():
    assert new_spend() == {"steps": 0, "seconds": 0.0, "in_tokens": 0, "out_tokens": 0}


def test_two_runs_do_not_share_a_spend_dict():
    """`new_spend()` must not hand back the module-level ZERO."""
    a, b = new_spend(), new_spend()
    a["steps"] = 99
    assert b["steps"] == 0


def test_the_reducer_adds_rather_than_replaces():
    """The whole point: two fan-out branches both really did spend.

    A replacing reducer would make the graph run and silently undercount, which
    is the one failure that would make the fan-out look cheaper than it is.
    """
    merged = merge_spend(
        spent(steps=1, seconds=2.0, in_tokens=100, out_tokens=10),
        spent(steps=1, seconds=3.5, in_tokens=200, out_tokens=20),
    )
    assert merged == {"steps": 2, "seconds": 5.5, "in_tokens": 300, "out_tokens": 30}


def test_the_reducer_tolerates_a_missing_side():
    """LangGraph calls a reducer with `None` on the first write to a field."""
    one = spent(steps=1, in_tokens=5)
    assert merge_spend(None, one) == merge_spend(one, None) == one


@pytest.mark.parametrize(
    ("spend", "expected"),
    [
        (spent(steps=3), STEP_CEILING),
        (spent(seconds=10.0), WALL_CLOCK),
        (spent(in_tokens=60, out_tokens=60), TOKEN_CEILING),
        (spent(steps=2, seconds=9.9, in_tokens=99), ""),
    ],
)
def test_each_ceiling_fires_on_its_own_currency(spend, expected):
    b = Budget(max_steps=3, max_seconds=10.0, max_tokens=100)
    assert b.exceeded(spend) == expected


def test_a_run_that_blows_two_ceilings_reports_the_same_one_every_time():
    """Order is fixed so the report is pinnable, not so steps are 'more important'."""
    b = Budget(max_steps=3, max_seconds=10.0, max_tokens=100)
    both = merge_spend(spent(steps=5), spent(seconds=50.0))
    assert b.exceeded(both) == STEP_CEILING
    assert b.exceeded(both) == STEP_CEILING


def test_exceeded_never_raises_on_a_partial_spend():
    """Workers write partial updates; a ceiling that raises is not a ceiling."""
    assert Budget().exceeded({}) == ""
    assert Budget().exceeded({"steps": 1}) == ""


def test_remaining_is_floored_at_zero():
    """A worker asking 'how much is left' after an overrun must not see a negative."""
    b = Budget(max_steps=2, max_seconds=1.0, max_tokens=10)
    over = spent(steps=5, seconds=9.0, in_tokens=50, out_tokens=50)
    assert b.remaining(over) == {"steps": 0, "seconds": 0.0, "tokens": 0}


def test_tokens_are_the_sum_of_both_directions():
    """Context is billed too -- a fan-out that re-sends the same context pays twice."""
    assert tokens(spent(in_tokens=1000, out_tokens=250)) == 1250


def test_the_dollar_figure_is_a_conversion_and_says_so():
    """Six decimal places, because a run costs a fraction of a cent.

    Rounding to cents would report every run as $0.00, which reads as 'free'
    rather than as 'small', and those are different claims.
    """
    s = summary(spent(in_tokens=1_000_000, out_tokens=1_000_000), Budget())
    assert s["usd"] == pytest.approx(0.40)
    assert s["usd_rate_assumed"] == {"in": 0.20, "out": 0.20}
    assert usd(spent(in_tokens=100)) > 0.0


def test_the_summary_carries_the_limits_it_was_measured_against():
    """A cost with no ceiling next to it cannot be read as 'nearly exhausted'."""
    s = summary(spent(steps=1), Budget(max_steps=7, max_seconds=8.0, max_tokens=9))
    assert s["limits"] == {"max_steps": 7, "max_seconds": 8.0, "max_tokens": 9}
    assert s["remaining"]["steps"] == 6
