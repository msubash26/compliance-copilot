"""One budget, three currencies, shared by every worker in the graph.

The prep plan asks for a "cost and step ceiling — hard-fail at N steps or $X,
with a partial result returned rather than an exception". There is no per-token
price on a 3090, so a dollar ceiling here would be a step ceiling with a dollar
sign painted on it. What is actually scarce is measured instead:

    steps    graph transitions, the thing a loop burns          (F4, F9)
    seconds  wall clock, the thing a serialising server burns   (research 1)
    tokens   context and generation, the thing a fan-out burns

and the dollar figure is produced by **converting** tokens once, through a rate
that is written down as an assumption rather than passed off as a measurement.
That way the ceiling is demonstrably a cost ceiling, and the one number in it
that this machine cannot observe is visibly the one that was assumed.

Two design points that are not obvious until the graph runs.

**Limits are configuration; spend is state.** The limits never change during a
run, so they travel in `RunnableConfig["configurable"]` and never touch the
checkpointer. The spend does change, so it lives in graph state -- and therefore
is a plain dict of primitives, not a dataclass. A checkpointer serialises state,
and a dataclass in state fails at the persistence boundary rather than at
construction, which is a long way from where the mistake was made.

**Spend needs a reducer, because fan-out writes it concurrently.** Two branches
of a `Send` fan-out both return a spend for the same super-step. Without a
reducer LangGraph raises `InvalidUpdateError` on the second write; with a
last-write-wins reducer the graph runs and silently loses one branch's cost,
which is worse. `merge_spend` adds.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# What a 9B-class model costs on a hosted endpoint, USD per million tokens.
#
# **This is a stated assumption, not a measurement, and not a quote.** Nothing on
# this workstation can observe a price; the figure is an order-of-magnitude
# anchor for a 9B-class open-weights endpoint, used so that the ceiling converts
# to a currency instead of pretending tokens are money. Override it with a real
# contracted rate before quoting any dollar figure outside this repo:
#
#     REGOPS_USD_PER_MTOK_IN=0.18 REGOPS_USD_PER_MTOK_OUT=0.18 uv run ...
USD_PER_MTOK_IN = float(os.environ.get("REGOPS_USD_PER_MTOK_IN", "0.20"))
USD_PER_MTOK_OUT = float(os.environ.get("REGOPS_USD_PER_MTOK_OUT", "0.20"))

# The three defaults. Steps is per *worker visit*, not per graph transition, so
# it is smaller than Day 6's 12: five workers each taking two turns is ten.
MAX_STEPS = 24
MAX_SECONDS = 600.0
MAX_TOKENS = 120_000

ZERO: dict = {"steps": 0, "seconds": 0.0, "in_tokens": 0, "out_tokens": 0}

# The three ceilings, in the order they are checked. `stopped_by` uses these
# names, and they extend Day 6's vocabulary rather than replacing it: `Run`
# already reports "step_ceiling" and "wall_clock".
STEP_CEILING = "step_ceiling"
WALL_CLOCK = "wall_clock"
TOKEN_CEILING = "token_ceiling"


@dataclass(frozen=True)
class Budget:
    """The limits. Configuration, so it never enters graph state."""

    max_steps: int = MAX_STEPS
    max_seconds: float = MAX_SECONDS
    max_tokens: int = MAX_TOKENS

    def exceeded(self, spend: dict) -> str:
        """Which ceiling has been passed, or "" -- never raises, never guesses.

        Checked in a fixed order so a run that blows two ceilings in the same
        super-step reports the same one every time. A ceiling that reports
        non-deterministically is not something a test can pin.
        """
        if spend.get("steps", 0) >= self.max_steps:
            return STEP_CEILING
        if spend.get("seconds", 0.0) >= self.max_seconds:
            return WALL_CLOCK
        if tokens(spend) >= self.max_tokens:
            return TOKEN_CEILING
        return ""

    def remaining(self, spend: dict) -> dict:
        """What is left, floored at zero. For a worker deciding how hard to try."""
        return {
            "steps": max(0, self.max_steps - spend.get("steps", 0)),
            "seconds": max(0.0, round(self.max_seconds - spend.get("seconds", 0.0), 3)),
            "tokens": max(0, self.max_tokens - tokens(spend)),
        }


def new_spend() -> dict:
    """A fresh, JSON-shaped spend. Callers must not share one dict between runs."""
    return dict(ZERO)


def spent(*, steps: int = 0, seconds: float = 0.0, in_tokens: int = 0, out_tokens: int = 0) -> dict:
    """One worker's contribution, as a state update the reducer can merge."""
    return {
        "steps": steps,
        "seconds": round(seconds, 3),
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
    }


def merge_spend(left: dict | None, right: dict | None) -> dict:
    """The reducer. Adds, because two fan-out branches both really did spend.

    Registered on the state field with `Annotated[dict, merge_spend]`. Without
    it, concurrent writes from a `Send` fan-out are an `InvalidUpdateError`; with
    a replacing reducer they are a silent undercount, which is the failure mode
    that would make the fan-out look cheaper than it is -- precisely the number
    Day 7 exists to get right.
    """
    a, b = left or new_spend(), right or new_spend()
    return {
        "steps": a.get("steps", 0) + b.get("steps", 0),
        "seconds": round(a.get("seconds", 0.0) + b.get("seconds", 0.0), 3),
        "in_tokens": a.get("in_tokens", 0) + b.get("in_tokens", 0),
        "out_tokens": a.get("out_tokens", 0) + b.get("out_tokens", 0),
    }


def tokens(spend: dict) -> int:
    """Total tokens, which is what the token ceiling is denominated in."""
    return spend.get("in_tokens", 0) + spend.get("out_tokens", 0)


def usd(spend: dict) -> float:
    """The conversion, not an observation. See `USD_PER_MTOK_IN`.

    Rounded to six places rather than to cents: a single run of this graph costs
    a fraction of a cent at the assumed rate, and rounding to cents would report
    every run as $0.00 -- which reads as "free" rather than as "small", and those
    are different claims.
    """
    return round(
        spend.get("in_tokens", 0) / 1e6 * USD_PER_MTOK_IN
        + spend.get("out_tokens", 0) / 1e6 * USD_PER_MTOK_OUT,
        6,
    )


def summary(spend: dict, budget: Budget) -> dict:
    """Everything a result should carry about what the run cost."""
    return {
        **spend,
        "tokens": tokens(spend),
        "usd": usd(spend),
        "usd_rate_assumed": {"in": USD_PER_MTOK_IN, "out": USD_PER_MTOK_OUT},
        "limits": {
            "max_steps": budget.max_steps,
            "max_seconds": budget.max_seconds,
            "max_tokens": budget.max_tokens,
        },
        "remaining": budget.remaining(spend),
    }
