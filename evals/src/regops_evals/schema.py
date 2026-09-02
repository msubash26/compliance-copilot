"""The golden set's contract, as a Pydantic model rather than a convention.

A golden set is the one artifact in this project that is *only* as good as its
discipline: nothing downstream can detect a question whose answer is wrong, or a
gold span that quietly stopped resolving. So the file is validated on write and
again on read, and every field that could rot carries what is needed to detect
the rot.

Three fields exist purely because of things that already happened here:

- `span_sha256` -- Day 3 moved this corpus from 8,055 clauses to 11,171. A set
  that pins only `section_path` is pinned to a *parser*. The hash lets
  `regops-evals verify` say `moved` rather than silently scoring against a
  clause that is no longer the one the question was written from.
- `verification.human_reviewed` -- the prep plan says "hand-correct every one",
  which assumes a human. This flag is how the artifact stays honest about the
  fact that, so far, none has.
- `difficulty.near_duplicates_at_0_10` -- MAS issues near-identical AML/CFT
  notices per regulated entity class, so an item's difficulty is a measurable
  property of where it sits in the corpus, not a label someone assigned.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

QueryType = Literal["factual_lookup", "multi_hop", "comparative", "temporal", "negative"]

QUERY_TYPES: tuple[QueryType, ...] = (
    "factual_lookup",
    "multi_hop",
    "comparative",
    "temporal",
    "negative",
)

# Declared before generation, so the mix is a decision and not an outcome (Day 4 plan, Phase 1).
STRATIFICATION: dict[QueryType, int] = {
    "factual_lookup": 45,
    "multi_hop": 30,
    "comparative": 25,
    "temporal": 15,
    "negative": 35,
}

# Why a negative is genuinely unanswerable from this corpus. Five sources, so the
# negative set is not 35 variations of one trick.
AbsenceReason = Literal[
    "other_jurisdiction",  # HKMA/FCA/MAS-adjacent regulator we did not fetch
    "out_of_scope_instrument",  # an Act or Regulation; the corpus is notices and guidelines
    "withdrawn_requirement",  # cancelled by a notice the corpus does hold
    "invented_specific",  # a plausible but fabricated threshold, deadline or form number
    "unregulated_topic",  # something MAS does not regulate at all
]


def span_hash(text: str) -> str:
    """Hash of a gold span's text, whitespace-normalised.

    Normalised because re-parsing legitimately changes line wrapping without
    changing the clause. What we want to detect is a *different clause*, not a
    different rendering of the same one.
    """
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


class GoldSpan(BaseModel):
    """One clause that answers the question, pinned three ways."""

    model_config = {"extra": "forbid"}

    doc_id: str
    section_path: str
    span_sha256: str
    why: str = Field(min_length=3, description="what this clause contributes to the answer")

    @property
    def section_uid(self) -> str:
        return f"{self.doc_id}:{self.section_path}"


class Difficulty(BaseModel):
    """Measured, not assigned."""

    model_config = {"extra": "forbid"}

    near_duplicates_at_0_10: int = Field(ge=0)
    vocab_overlap: float = Field(ge=0.0, le=1.0, description="question/span content-word Jaccard")


class Provenance(BaseModel):
    model_config = {"extra": "forbid"}

    generator: str
    corpus_manifest_sha: str
    index_built_at: str
    parser: str


class Verification(BaseModel):
    """What was checked, by what, and what a person still owes this item."""

    model_config = {"extra": "forbid"}

    span_exists: bool | None = None
    answerable_from_span: bool | None = None
    no_leakage: bool | None = None
    not_answerable_without_span: bool | None = None
    verifier: str | None = None
    status: Literal["unverified", "machine_verified", "flagged", "human_verified"] = "unverified"
    human_reviewed: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    failures: list[str] = Field(default_factory=list)


class GoldenItem(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(pattern=r"^gs-\d{4}$")
    question: str = Field(min_length=15)
    answer: str = Field(min_length=2)
    query_type: QueryType
    gold_spans: list[GoldSpan] = Field(default_factory=list)
    entity_class: str | None = None
    difficulty: Difficulty | None = None
    absence_reason: AbsenceReason | None = None
    provenance: Provenance
    verification: Verification = Field(default_factory=Verification)
    notes: str = ""

    @field_validator("question")
    @classmethod
    def _one_question(cls, v: str) -> str:
        if not v.strip().endswith("?"):
            raise ValueError("question must end with '?'")
        return v.strip()

    @model_validator(mode="after")
    def _spans_match_type(self) -> GoldenItem:
        if self.query_type == "negative":
            if self.gold_spans:
                raise ValueError("a negative has no gold span -- that is what makes it negative")
            if self.absence_reason is None:
                raise ValueError("a negative must say why it is unanswerable")
        else:
            if not self.gold_spans:
                raise ValueError(f"{self.query_type} needs at least one gold span")
            if self.absence_reason is not None:
                raise ValueError("absence_reason belongs to negatives only")
        # The two types that are defined by spanning more than one clause.
        if self.query_type in ("multi_hop", "comparative") and len(self.gold_spans) < 2:
            raise ValueError(f"{self.query_type} needs 2+ gold spans")
        return self


def read_jsonl(path: Path) -> list[GoldenItem]:
    """Read and validate. A malformed line names itself rather than failing anonymously."""
    items: list[GoldenItem] = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            items.append(GoldenItem.model_validate_json(line))
        except Exception as exc:
            raise ValueError(f"{path}:{n}: {exc}") from exc
    seen: set[str] = set()
    for it in items:
        if it.id in seen:
            raise ValueError(f"{path}: duplicate id {it.id}")
        seen.add(it.id)
    return items


def write_jsonl(path: Path, items: list[GoldenItem]) -> None:
    """Write validated. Round-tripping through the model is the validation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(it.model_dump(mode="json"), ensure_ascii=False) for it in items]
    path.write_text("\n".join(lines) + "\n")
