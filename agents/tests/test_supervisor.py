"""The supervisor's control flow, without a model and without a server.

Everything the graph decides -- which worker runs, when a run goes backwards, when
a ceiling fires, what a `Send` fan-out is given -- is decided from state, so all
of it is testable with a fake toolbox. What is *not* tested here is whether the
model answers well; that is measured in `results/day7/`, not asserted.
"""

from __future__ import annotations

import json

import pytest
from regops_agents.budget import Budget, merge_findings, merge_spend, new_spend, spent
from regops_agents.llm import Reply
from regops_agents.structured import Answer, Citation
from regops_agents.supervisor import build, node_approve, node_check, node_fan_out
from regops_agents.workers import (
    TRUNCATED,
    Toolbox,
    candidate_clauses,
    check,
    search,
    topic_terms,
)


class FakeTool:
    """One MCP tool, with a scripted reply per argument set."""

    def __init__(self, fn):
        self.fn = fn
        self.calls: list[dict] = []

    async def ainvoke(self, args: dict):
        self.calls.append(args)
        return self.fn(args)


class FakeIndex:
    """Just enough of `Index` for layer 2: a set of uids that exist."""

    def __init__(self, uids):
        self.uids = set(uids)

    def clause_by_uid(self, uid):
        return object() if uid in self.uids else None


def box_with(**tools) -> Toolbox:
    return Toolbox(index="x", tools={k: FakeTool(v) for k, v in tools.items()})


# -- the citation checker ---------------------------------------------------


class TestCheck:
    def test_it_strips_the_bad_citation_and_keeps_the_good_one(self):
        """A checker that can only reject is a gate; one that can strip is a filter."""
        box = box_with()
        box.ix = FakeIndex({"aaa:1.1"})
        ans = Answer(
            answer="x",
            citations=[
                Citation(doc_id="aaa", section_path="1.1"),
                Citation(doc_id="zzz", section_path="9"),
            ],
            sufficient=True,
        )
        violations, good = check(ans, box)
        assert len(violations) == 1 and "zzz" in violations[0]
        assert good == [{"doc_id": "aaa", "section_path": "1.1"}]

    def test_nothing_parseable_is_a_shape_violation_not_a_crash(self):
        assert check(None, box_with())[0] == ["shape: the extractor returned nothing parseable"]


# -- F14: the truncation cap belongs to the caller --------------------------


class TestSearchBackOff:
    def test_a_result_truncated_out_of_json_is_retried_smaller(self):
        """The graph parses these; a cut mid-JSON is no answer, not a short one."""
        seen = []

        def tool(args):
            seen.append(args["top_k"])
            if args["top_k"] > 10:
                return '{"hits": [{"doc_id": "a"' + TRUNCATED + " 99,000 characters returned]"
            return json.dumps({"hits": [{"doc_id": "a", "section_path": "1"}]})

        box = box_with(search_notices=tool)
        hits, notes = _run(search("q", box, 30))
        assert seen == [30, 15, 8]
        assert len(hits) == 1
        assert any("truncated out of JSON" in n for n in notes)

    def test_it_gives_up_rather_than_looping(self):
        box = box_with(search_notices=lambda a: "not json at all")
        hits, notes = _run(search("q", box, 30))
        assert hits == []
        assert any("unparseable" in n for n in notes)


def _run(coro):
    """Drive one coroutine from a sync test. These touch no event-loop state."""
    import asyncio

    return asyncio.run(coro)


# -- the fan-out ------------------------------------------------------------


class TestFanOut:
    def test_hits_are_grouped_by_document_not_deduplicated_to_one(self):
        """The asymmetry that made a coverage sweep wrong; see `candidate_clauses`."""
        state = {
            "question": "topic",
            "hits": [
                {"doc_id": "a", "section_path": "8.1", "title": "A"},
                {"doc_id": "a", "section_path": "8.2", "title": "A"},
                {"doc_id": "b", "section_path": "8.1", "title": "B"},
            ],
        }
        cmd = node_fan_out(state, {"configurable": {}})
        payloads = [s.arg for s in cmd.goto]
        assert len(payloads) == 2
        by_doc = {p["doc"]["doc_id"]: p["doc"]["hits"] for p in payloads}
        assert [h["section_path"] for h in by_doc["a"]] == ["8.1", "8.2"]

    def test_no_hits_goes_straight_to_the_synthesiser(self):
        """An empty fan-out must still produce an answer, not an empty `goto`."""
        cmd = node_fan_out({"question": "t", "hits": []}, {"configurable": {}})
        assert cmd.goto == ["synthesise"]


class TestBranchRetrieval:
    def test_the_branch_adds_its_own_document_s_topical_clauses(self):
        """Symmetry: a branch must not depend on what the global top-k gave it.

        Document `b` was handed only the definition clause by the global search.
        Its own obligation listing contains the clause that matters, and without
        this the branch reports a document that covers the topic as silent.
        """
        page = json.dumps(
            {
                "obligations": [
                    {"section_path": "8.1", "heading": "PEP", "text": "close associate means"},
                    {
                        "section_path": "8.2",
                        "heading": "PEP",
                        "text": "shall determine if a customer is a politically exposed person",
                    },
                ],
                "next_cursor": None,
            }
        )
        box = box_with(list_obligations=lambda a: page)
        doc = {"doc_id": "b", "hits": [{"doc_id": "b", "section_path": "8.1"}]}
        paths = _run(candidate_clauses(doc, box, topic_terms("politically exposed persons")))
        assert paths[0] == "8.1"  # what search gave it, kept and first
        assert "8.2" in paths  # what it found for itself

    def test_a_topic_word_that_matches_everything_is_not_enough(self):
        """One term matches most of an AML notice; the threshold is two."""
        page = json.dumps(
            {
                "obligations": [{"section_path": "1.1", "text": "a person shall"}],
                "next_cursor": None,
            }
        )
        box = box_with(list_obligations=lambda a: page)
        doc = {"doc_id": "b", "hits": []}
        assert _run(candidate_clauses(doc, box, topic_terms("politically exposed persons"))) == []


# -- ceilings ---------------------------------------------------------------


class TestCeilings:
    @pytest.mark.parametrize("spend", [spent(steps=99), spent(in_tokens=10**9)])
    def test_an_exhausted_budget_routes_to_the_synthesiser_rather_than_raising(self, spend):
        """The prep plan's words: a partial result returned rather than an exception."""
        import asyncio

        from regops_agents.supervisor import node_router

        cfg = {
            "configurable": {
                "toolbox": box_with(),
                "budget": Budget(max_steps=3, max_seconds=1e9, max_tokens=100),
                "t0": 1e18,  # far future, so wall clock cannot be what fires
                "approve": False,
            }
        }
        cmd = asyncio.run(node_router({"question": "q", "spend": spend}, cfg))
        assert cmd.goto == "synthesise"
        assert cmd.update["stopped_by"] in {"step_ceiling", "token_ceiling"}


# -- rerouting --------------------------------------------------------------


def _check_cfg(uids, **budget):
    box = box_with()
    box.ix = FakeIndex(uids)
    return {
        "configurable": {
            "toolbox": box,
            "budget": Budget(**budget) if budget else Budget(),
            "t0": 1e18,
            "approve": False,
        }
    }


class TestRerouting:
    def _state(self, **kw):
        base = {
            "question": "q",
            "draft": "d",
            "sufficient": True,
            "citations": [{"doc_id": "zzz", "section_path": "9"}],
            "retries": 0,
            "spend": new_spend(),
        }
        return base | kw

    async def test_an_unresolvable_citation_sends_the_run_back_once(self):
        """F5's fix: the graph takes the recovery path instead of asking the human."""
        cmd = await node_check(self._state(), _check_cfg(set()))
        assert cmd.goto == "retrieve"
        assert cmd.update["retries"] == 1
        assert cmd.update["query"] == "q"  # the user's own words, not the rewrite

    async def test_it_does_not_send_it_back_twice(self):
        cmd = await node_check(self._state(retries=1), _check_cfg(set()))
        assert cmd.goto == "synthesise"

    async def test_an_insufficient_answer_also_sends_it_back(self):
        """Usually the router's rewrite missing the clause's wording, not a silent corpus."""
        state = self._state(sufficient=False, citations=[])
        cmd = await node_check(state, _check_cfg(set()))
        assert cmd.goto == "retrieve"
        assert "did not answer" in cmd.update["notes"][-1]

    async def test_a_clean_answer_goes_forward(self):
        state = self._state(citations=[{"doc_id": "aaa", "section_path": "1.1"}])
        cmd = await node_check(state, _check_cfg({"aaa:1.1"}))
        assert cmd.goto == "synthesise"
        assert cmd.update["violations"] == []

    async def test_the_plan_and_execute_variant_never_reroutes(self):
        """The whole difference between the two architectures is this one edge."""
        from regops_agents.supervisor import _check_once

        cmd = await _check_once(self._state(), _check_cfg(set()))
        assert cmd.goto == "synthesise"
        assert cmd.update["violations"]  # it still *reports* the violation


# -- the graph itself -------------------------------------------------------


class TestGraph:
    def test_both_variants_compile_with_the_same_nodes(self):
        a = set(build().compile().get_graph().nodes)
        b = set(build(plan_and_execute=True).compile().get_graph().nodes)
        assert a == b
        assert {"router", "retrieve", "extract", "check", "fan_out", "inspect"} <= a

    def test_the_spend_reducer_is_registered_on_the_state(self):
        """Without it a `Send` fan-out is an InvalidUpdateError or a silent undercount.

        `get_type_hints(include_extras=True)` rather than `__annotations__`: the
        module uses `from __future__ import annotations`, so the raw annotations
        are strings and the `Annotated` metadata is not there to find.
        """
        from typing import get_type_hints

        from regops_agents.supervisor import SupervisorState

        hints = get_type_hints(SupervisorState, include_extras=True)
        assert merge_spend in hints["spend"].__metadata__
        assert hints["findings"].__metadata__  # `add`, for the same reason


def test_a_reply_converts_itself_into_a_state_update():
    """The budget is only honest if every call debits it."""
    r = Reply(content="x", seconds=1.25, in_tokens=10, out_tokens=3)
    assert r.spend() == {"steps": 1, "seconds": 1.25, "in_tokens": 10, "out_tokens": 3}


# -- human in the loop ------------------------------------------------------


def _gated_cfg():
    """`_check_cfg` closes the approval gate; these tests are about it being open."""
    cfg = _check_cfg(set())
    cfg["configurable"]["approve"] = True
    return cfg


class TestApproval:
    def _state(self, **kw):
        base = {
            "question": "which documents cover X?",
            "query": "X obligation",
            "findings": [{"doc_id": "a", "title": "A", "covered": True, "section_path": "8.2"}],
            "retries": 0,
        }
        return base | kw

    def test_approval_goes_forward(self, monkeypatch):
        monkeypatch.setattr("regops_agents.supervisor.interrupt", lambda _: "approve")
        cmd = node_approve(self._state(), _gated_cfg())
        assert cmd.goto == "synthesise" and cmd.update["approved"] is True

    def test_a_rejection_puts_its_reason_into_the_query_and_re_runs(self, monkeypatch):
        """A rejection that only annotates the answer is a confirmation dialog.

        Measured end to end: rejecting with *"you missed the trust companies and
        VCC notices"* re-ran the sweep and returned TCA-N03 and VCC-N01, neither
        of which the first sweep had found.
        """
        monkeypatch.setattr("regops_agents.supervisor.interrupt", lambda _: "you missed the VCCs")
        cmd = node_approve(self._state(), _gated_cfg())
        assert cmd.goto == "retrieve"
        assert cmd.update["query"] == "X obligation you missed the VCCs"
        assert cmd.update["findings"] is None  # the reset sentinel, not an append
        assert cmd.update["retries"] == 1

    def test_a_second_rejection_answers_rather_than_looping(self, monkeypatch):
        """A reviewer who keeps rejecting is a conversation, not a graph loop."""
        monkeypatch.setattr("regops_agents.supervisor.interrupt", lambda _: "still wrong")
        cmd = node_approve(self._state(retries=1), _gated_cfg())
        assert cmd.goto == "synthesise" and cmd.update["approved"] is False

    def test_the_gate_can_be_closed_for_unattended_runs(self):
        """The comparison harness must not block on a human."""
        cfg = _check_cfg(set())
        cfg["configurable"]["approve"] = False
        cmd = node_approve(self._state(), cfg)
        assert cmd.goto == "synthesise" and "skipped" in cmd.update["notes"][0]


class TestFindingsReducer:
    def test_branches_merge_and_a_rerun_replaces_rather_than_duplicates(self):
        first = [{"doc_id": "a", "covered": False}, {"doc_id": "b", "covered": True}]
        second = [{"doc_id": "a", "covered": True}]
        assert merge_findings(first, second) == [
            {"doc_id": "a", "covered": True},
            {"doc_id": "b", "covered": True},
        ]

    def test_none_clears(self):
        """`operator.add` cannot express 'start again' -- appending [] is a no-op."""
        assert merge_findings([{"doc_id": "a"}], None) == []
