# Day 4 — The golden set

**Repo:** `compliance-copilot` (member `regops-evals`) · **Date:** 2026-09-04
**Budget:** ~4.5h build + 1h write-up, plus a human review pass the plan sizes but cannot do

> The prep plan calls this "the least glamorous day and the highest-leverage one. Everything
> downstream is unmeasurable without it." Day 5's whole deliverable — *different architectures
> win on different query types* — is a property of this artifact, not of the retriever.

---

## Context

Day 3 delivered the index this day measures against: 463 documents / 9,043 pages → 11,171
clauses → 22,090 chunks → 44,180 vectors, with BM25 and HNSW in one 433 MB DuckDB file. The
four MCP tools serve it unchanged.

### Carried forward from Days 1–3

- **`diff_versions` still has no version pairs.** Day 3 built and tested idempotent
  re-ingestion, but the corpus is a single fetch: **0 documents have more than one version
  row**. ADR-004's empty state stands. This constrains the `temporal` query type — see problem 3.
- **Clause paths moved once already.** Day 3 took sections from 8,055 to 11,171. A golden set
  that pins `section_path` is pinned to a *parser*, not just a corpus.
- **Letter-suffixed clauses (`6.14A`) are merged into their parent** — 190 of 11,171 sections
  (1.7%). Day 3 deferred this to "whether Day 4's golden set says it matters". Day 4 is where
  that gets answered.
- **Ollama serialises.** Stages run one model at a time; a swap costs a load. Batch by model.

### Research completed before planning (ADR-002's rule)

Every number below was measured today against the real index.

**1. A naively generated golden set is saturated, and would make Day 5 measure nothing.**
Twelve questions generated from randomly sampled clauses, then searched:

| | recall@1 | recall@5 | recall@20 |
|---|---|---|---|
| BM25 | 75% | **92%** | 92% |
| dense (`nomic-embed-text`) | 58% | **92%** | 100% |

Both arms are at ceiling by k=5 before any hybrid, rerank or contextual variant is applied.
A sweep over seven configurations against this set would produce seven identical rows. The
cause is mechanical: a question generated *from* a clause reuses that clause's vocabulary, so
lexical retrieval cannot lose. **Difficulty has to be engineered in deliberately**, and the
plan below is mostly about how.

**2. The corpus supplies the difficulty mechanism: entity-class near-duplication.** MAS issues
near-identical AML/CFT notices per regulated entity class. Measured against Notice 626's clause
6.14 (identifying beneficial owners), by cosine distance over the chunk embeddings:

```
0.0217  Notice 626      banks                    <- the answer
0.0446  Notice 1014     merchant banks
0.0599  Notice PSM-N01  payment service managers
0.0769  SFA 03AA-N01    the Depository
0.0836  Notice 824      finance companies
0.0959  Notice FAA-N06  financial advisers
0.0973  SFA 13-N01      approved trustees
0.1005  Guidelines to Notice 626
0.1043  Notice 626A     credit/charge card licensees
0.1081  Notice PSN01    payment services
0.1081  Notice PSN02    payment services
0.1092  PSN01AA
```

**Seven clauses from seven different notices sit within cosine 0.10** of the target, twelve
within 0.11, and there are 12+ such parallel notices in the corpus. The texts differ mainly in
*which entity they bind*. A question about a merchant bank's obligation therefore ships with
eleven near-perfect distractors, and answering it needs the right *document*, not just the
right topic. That is exactly where metadata filtering and reranking earn their keep, and it is
the natural source of headroom this benchmark needs.

**3. Multi-hop is well grounded.** Of 11,171 clauses: **1,836 (16.4%) cite another MAS Notice**,
**1,563 (14.0%) cite a paragraph number**, 772 (6.9%) cite a statute.

**4. Temporal is grounded in-document, but not as version diffs.** 0 documents have >1 version.
What does exist: **21 documents carry amendment-history endnotes** ("MAS Notice 120 (Amendment)
2015, dated 30 October 2015 with effect from 1 November 2015, except paragraphs 2(z) and 4
which are effective from 30 June 2016"), **59 `[Deleted by MAS Notice ...]` markers**, **422
clauses saying "with effect from"**, and effective dates spanning **1973-11-01 to 2027-01-01** —
including a notice not yet in force. So temporal questions are answerable about *stated*
effective dates and *recorded* amendments. They are not answerable as "diff these two stored
versions", and the plan will not pretend otherwise.

**5. Cost is not the constraint.** Generation on `qwen3.5:9b` (`think=False`): **1.5 s/question**
→ 150 questions in ~4 minutes. Verification on `qwen3.8` once warm: **0.3–0.4 s/call** → ~1
minute, behind a ~15s model load. The expensive resource on Day 4 is human attention, not GPU.

---

## The four problems Day 4 has to solve

**1. The set must have headroom, without being rigged.**
There are two ways to fake this and both are worse than a saturated set. Discarding questions
that BM25 happens to answer tunes the benchmark to embarrass a baseline. Selecting gold spans
from what retrieval returned makes the ground truth a function of the system under test.
*Resolution:* gold spans are always the clause the question was generated **from**, fixed
before any retrieval runs. Headroom comes from adding harder **categories** — entity
disambiguation, multi-hop, comparative — never from deleting items a baseline got right. A
saturation gate measures the spread and reports it; it does not filter on it.

**2. "Hand-correct every one" assumes a human, and I am not one.**
*Resolution:* say so on the artifact. Every item carries a `verification` block recording what
was checked mechanically, by which model, and `human_reviewed: false` until a person says
otherwise. Verification uses a **different model from the generator** (`qwen3.8` verifying
`qwen3.5:9b`) because a model agreeing with itself is not evidence. The plan produces a ranked
**review queue** — lowest-confidence items first — so the prep plan's 3 hours of human
attention lands where it changes the artifact, rather than being spread evenly over 150 items
of which most are fine.

**3. `temporal` cannot mean "what changed between versions".**
*Resolution:* define the label as **stated-time questions** — when a requirement takes effect,
which amendment deleted a paragraph, whether a notice is yet in force — grounded in the
amendment endnotes and effective dates measured above. The version-diff variant is recorded as
explicitly out of scope with a pointer to ADR-004, and becomes available on the first re-fetch
that finds changed bytes. Mislabelling one as the other would quietly corrupt Day 5's
per-query-type table.

**4. A golden set silently rots when the parser changes.**
Day 3 moved 8,055 clauses to 11,171. `doc_id` is URL-derived and stable (ADR-012), but
`section_path` belongs to whatever parsed the document.
*Resolution:* every item pins `doc_id` **and** `section_path` **and** a `span_sha256` of the
gold text. `regops-evals verify --index` re-binds every span against a live index and reports
three outcomes — resolved / moved / missing — so drift is a failing check rather than a slow
decay in the numbers.

---

## Phase 0 — Housekeeping · 15 min

- [x] `gh auth status` — drifts back to `99Tungsten99`
- [x] `./scripts/stack.sh ps` — 7 services; LangFuse needed for generation traces
- [x] Confirm the index is the compacted 433 MB file and `regops-ingest trace` still works
- [x] Re-read ADR-004 (no fake versions), ADR-012 (doc_id rules), ADR-014 (clause = parent)

## Phase 1 — Schema, and the artifact contract · 45 min

- [x] `evals/src/regops_evals/schema.py` — a Pydantic model, so the JSONL is validated on write
      and on read rather than by convention:

```jsonc
{
  "id": "gs-0001",
  "question": "...",
  "answer": "...",
  "query_type": "factual_lookup|multi_hop|comparative|temporal|negative",
  "gold_spans": [                       // empty for negatives
    {"doc_id": "1b9b9f6db2876069", "section_path": "6.14",
     "span_sha256": "...", "why": "states the identification duty"}
  ],
  "entity_class": "banks",              // the discriminator for near-duplicate notices
  "difficulty": {"near_duplicates_at_0_10": 7, "vocab_overlap": 0.21},
  "absence_reason": null,               // negatives only: why it is genuinely not in scope
  "provenance": {"generator": "qwen3.5:9b", "corpus_manifest_sha": "...",
                 "index_built_at": "...", "parser": "regops-ingest@<git-sha>"},
  "verification": {"span_exists": true, "answerable_from_span": true, "no_leakage": true,
                   "verifier": "qwen3.8:latest", "status": "machine_verified",
                   "human_reviewed": false, "confidence": 0.82},
  "notes": ""
}
```

- [x] `golden/v1/golden.jsonl` + `golden/v1/README.md` stating exactly what was and was not
      human-reviewed. **Versioned by directory**, so v2 can exist without rewriting history.
- [x] Stratification targets, written down before generation so the mix is a decision and not
      an outcome:

| type | n | grounded in |
|---|---|---|
| `factual_lookup` | 45 | one clause |
| `multi_hop` | 30 | 2+ clauses, at least one reached by cross-reference |
| `comparative` | 25 | 2+ parallel entity-class notices |
| `temporal` | 15 | amendment endnotes, effective dates |
| `negative` | 35 | nothing — and that is the point |
| **total** | **150** | |

  Negatives are 23% of the set. The prep plan is right that they are undervalued: "how often
  does it correctly say I don't know" is the question a regulated employer actually asks.

## Phase 2 — Candidate selection · 45 min

- [x] Sample clauses stratified by `doc_type`, clause length, and **near-duplicate count**
      (computed from the HNSW index), so the set deliberately spans easy and contested regions
      rather than sampling uniformly into the easy one.
- [x] Exclude front matter (`section_path` `0`), the 237 opaque `#N` paths, and clauses under
      ~200 characters — none of them carry a citable obligation.
- [x] For `multi_hop`: pick clauses whose text cites another notice or paragraph, resolve the
      reference to a real `doc_id`/`section_path`, and keep only pairs where **both** ends
      resolve. An unresolvable cross-reference is a finding, not a question.
- [x] For `comparative`: pick a topic, then take the same clause across 2–3 entity classes from
      the parallel notices measured above.
- [x] For `temporal`: draw from the 21 amendment-history documents, the 59 `[Deleted by ...]`
      markers, and the forward-dated notice.

## Phase 3 — Generation · 75 min

- [x] One prompt per query type, each with explicit **anti-leakage** rules: never name the
      notice or clause number, never reuse the clause's rarest terms, ask in the language a
      compliance officer would use out loud.
- [x] For every item in a contested region, the question **must** name the entity class
      ("a merchant bank", "a payment service provider"). This is what makes the near-duplicate
      distractors defeatable rather than unfair — the information needed to disambiguate is in
      the question.
- [x] **Negatives get their own generator and their own five sources**, each item carrying an
      `absence_reason`: another jurisdiction (HKMA/FCA); an instrument type outside the corpus
      (the corpus is notices and guidelines, not Acts or Regulations); a withdrawn requirement
      (the corpus holds a real cancellation notice); a plausible but invented threshold or
      deadline; a topic MAS does not regulate. A negative set made only of nonsense questions
      measures nothing — these have to be questions a person would actually ask.
- [x] Trace generation to LangFuse, sampled, reusing the Day 3 pattern.
- [x] Batch strictly by model. Generate everything with `qwen3.5:9b` before loading anything else.

## Phase 4 — Independent verification and the review queue · 60 min

- [x] **Verify with `qwen3.8`, not the generator.** Given only the question and the gold span,
      the verifier must independently produce the recorded answer. Disagreement is a flag, not
      a deletion.
- [x] Mechanical checks, all cheap and all decisive: gold span resolves; `span_sha256` matches;
      no notice or clause number leaked into the question (regex); answer entities present in
      the span; question is not answerable with the span **removed** (guards against questions
      answerable from general knowledge, which measure the model and not the retriever).
- [x] **Negative verification is the inverse and needs care**: search the corpus hard for each
      negative — BM25 and dense, top-20 — and have the verifier confirm that *no* returned
      clause answers it. A negative that turns out to be answerable is the most damaging item
      in the set, because it teaches the eval to reward abstention when abstention is wrong.
- [x] Emit `golden/v1/review_queue.md` — every item sorted by ascending confidence, with the
      gold span inline so a person can adjudicate without opening the PDF. **This is the
      artifact the prep plan's 3 hours should be spent on.**
- [x] Record how many items each check rejected. "The verifier disagreed on 14 of 150" is a
      more honest quality claim than a clean file.

## Phase 5 — Tests, drift, and the saturation gate · 45 min

- [x] Schema tests: every line validates; ids unique; stratification matches the declared
      targets; negatives have no `gold_spans` and every non-negative has at least one.
- [x] **`regops-evals verify --index`** — re-bind every gold span against a live index and
      report resolved / moved / missing. Runs in CI against a small fixture index, and by hand
      against the real one. This is the anti-rot check from problem 4.
- [x] **The saturation gate.** Measure BM25 and dense recall@5 over the finished set, per query
      type, and record it. If the aggregate is above ~80%, the set lacks headroom and the fix
      is to *add* contested and multi-hop items — never to remove items a baseline answered.
      Publishing this number is also Day 5's baseline row, computed before Day 5 can be
      tempted by it.
- [x] A `pytest` marker so the LLM-dependent generation tests are skipped in CI (no GPU there)
      while the schema, drift and stratification tests always run.

## Phase 6 — Write-up · 50 min

- [x] **ADR-017** — the golden set is machine-generated and machine-verified, with an explicit
      human-review boundary; why the verifier is a different model; why nothing is filtered by
      retrievability.
- [x] **ADR-018** — query-type taxonomy, and why `temporal` means stated-time rather than
      version-diff on this corpus (pointing at ADR-004).
- [x] **ADR-019** — difficulty is engineered from entity-class near-duplication; the measured
      distances; why this is fair rather than adversarial.
- [x] `evals/README.md`: the schema, the stratification table, the saturation baseline, and a
      plain statement of what a person still has to check.
- [x] Update `initial-setup.md`; commit, push both repos, confirm CI green.

---

## Deliverables

`golden/v1/golden.jsonl` — 150 validated triples, stratified and provenance-stamped · a Pydantic
schema · an independent verification pass with counts · a ranked human review queue · a span
drift checker · a published saturation baseline per query type · 3 ADRs · green CI.

## Decisions I would want a steer on

1. **Who does the human pass, and when.** The artifact is honest either way, but it is labelled
   differently. *Recommendation: ship v1 as machine-verified with the review queue attached, and
   let the human pass produce v1.1.* Day 5 can run against v1 immediately; a benchmark whose
   items later change slightly is fine as long as the version is pinned in the results.
2. **150 items, or fewer and better?** *Recommendation: keep 150.* Per-query-type cells need
   enough items to be readable — 15 temporal items is already a thin cell, and cutting the total
   makes Day 5's table anecdote rather than measurement.
3. **Should the golden set pin chunk ids as well as clause ids?** *Recommendation: no.* Clauses
   are the citable unit (ADR-014) and chunk boundaries are a tunable Day 5 sweeps over. Pinning
   chunks would make the ground truth move whenever the chunker is tuned — the set would measure
   its own configuration.

## Risks

1. **The set is still too easy after Phase 3.** Mitigated by measuring it in Phase 5 rather than
   assuming, and by having a named remedy (add contested/multi-hop items) that does not corrupt
   the ground truth.
2. **The generator writes questions that leak their source.** The anti-leakage rules are checked
   mechanically, not trusted to the prompt.
3. **Negatives turn out to be answerable.** The most damaging failure here, so it gets the
   heaviest verification: an active search for the answer rather than a check that none was found.
4. **Cross-references do not resolve.** Only pairs where both ends resolve become `multi_hop`
   items; the rest are counted and reported, which is a finding about the corpus.

**Descope order if behind:** `temporal` → 8 items · `comparative` → 15 items · generation traces
→ summary span only. **Never cut** the negative set, the independent verifier, or the saturation
gate: the first is the day's distinctive claim, the second is what makes "verified" mean
anything, and the third is what tells Day 5 whether it can measure at all.

---

## Outcome

**Shipped.** `golden/v1/` — 150 items, stratified exactly to the declared targets, every gold
span pinned by `doc_id` + `section_path` + `span_sha256`, verified by a second model, with a
ranked review queue and a published saturation baseline. 60 new tests, 114 across the repo,
green. Three ADRs.

### The plan's central bet paid off, and the numbers say by how much

The plan was written around one measurement: a naive golden set is saturated (BM25 92%
recall@5, dense 92%), so Day 5 would have measured nothing. The finished set, same two
retrievers, same definitions:

| query type | bm25 hit@5 | dense hit@5 | bm25 full@5 | dense full@5 | n |
|---|---|---|---|---|---|
| `factual_lookup` | 0.733 | 0.733 | 0.733 | 0.733 | 45 |
| `multi_hop` | **0.800** | 0.600 | 0.167 | 0.167 | 30 |
| `comparative` | 0.560 | 0.560 | 0.160 | 0.160 | 25 |
| `temporal` | 0.400 | 0.333 | 0.400 | 0.333 | 15 |
| **overall** | **0.670** | **0.609** | **0.417** | **0.409** | 115 |

92% → 67%, and the per-type rows already diverge before Day 5 tunes anything. `full@5` at 0.16
on the multi-span types is the headroom the sweep spends.

### What the plan got wrong

**A shared clause number does not mean a shared topic.** Phase 2 assumed MAS's parallel AML/CFT
notices share a numbering scheme, so the same `section_path` could be lifted across entity
classes. It cannot: clause 11.7 is wire-transfer originator information in Notices 824 and 1014
and **correspondent accounts** in Notice 626A. The first comparative pass generated questions
comparing two things and an unrelated third — the verifier flagged 13 of 25, correctly. Measured
across all 196 shared paths in the family, the median maximum pairwise cosine distance within a
group is **0.330**: most shared paths are not parallel at all. Fixed by verifying alignment with
the vectors (≤ 0.25 leaves 73 groups); the shipped set's worst group went 0.474 → **0.246**.

**Long boilerplate defeats every length-based filter.** Definitions, scope paragraphs and
exemption schedules are lengthy, plausible and near-identical across notices, and bind nobody.
They produced comparative questions whose honest answer is "identically, it is the same
boilerplate". Fixed with an obligation-marker filter (*shall*, *must*, *is required to*) —
5,949 of 7,993 eligible clauses — applied to `factual_lookup` and `comparative` only, since the
other three types are legitimately grounded in clauses that state no duty.

**The closed-book check was measuring the wrong thing.** Phase 4 planned to flag questions the
verifier could answer unaided. Asked directly, `qwen3.8` claimed to know **45 of 115** — and then
produced generic regulatory boilerplate ("cybersecurity, data privacy and operational
resilience" where the clause says money-laundering risk). A model's self-report of knowledge is
no more evidence than a model's agreement with itself. Replaced by comparing the closed-book
answer against the gold answer: median overlap **0.083**, max **0.455**, **0 items** clear the
bar. The corpus is genuinely required — now as a measurement rather than an assumption.

**Three items leaked their source.** The plan said anti-leakage would be "checked mechanically,
not trusted to the prompt", and the first run proved the point: 3 of 115 questions named a notice
or instrument code. Recording the defect was not enough — the check moved *into* the generation
retry loop, where it can act. Final set: **0 leaks**, independently reconfirmed by `verify`.

### What held

- Costs were as estimated: generation 150 items in ~7 min, verification ~7.5 min, selection 83s.
- The negative set is the strongest part. **0 of 35 turned out to be answerable**, against a
  deliberately hard search (BM25 top-10 + dense top-10, 12 excerpts to the judge). Five distinct
  absence reasons, evenly spread.
- Span drift: **150/150 resolved, 0 moved, 0 missing**. The check that exists because Day 3 moved
  8,055 clauses to 11,171 now exits non-zero if it ever stops being true.
- The multi-hop pool was as measured — 467 guideline→notice hops from 120 source clauses, 129
  explicit citations from 46 — and only pairs where both ends resolve became items.

### Descope: none taken

All five query types shipped at their full declared counts. The plan's descope order
(`temporal` → 8, `comparative` → 15) was not needed.

### The three open decisions, as resolved

1. **Who does the human pass.** Shipped as recommended: v1 is machine-verified with
   `human_reviewed: false` asserted by a test, and `review_queue.md` ranks the ~28 contested
   items first. Day 5 can start now; a human pass produces v1.1.
2. **150 items.** Kept. The per-type cells are already thin at 15 temporal items, and the
   divergence in the table above needs them.
3. **Pin chunk ids?** No, as recommended. Clauses are the citable unit (ADR-014) and chunk
   boundaries are a parameter Day 5 sweeps over; pinning them would make the ground truth move
   whenever the chunker is tuned.

### Carried into Day 5

- **`comparative` is the least-verified type** (12 of 25 flagged). The questions need synthesis
  across spans and a single-pass judge is strictest there. Worth a human eye before that row is
  used to draw conclusions.
- **`multi_hop` leans on one cross-reference family** — guidelines citing their parent notice.
  Worth stating whenever that row is quoted.
- **A note on ADR numbering:** `regdocs-mcp` ADR-004 is the `diff_versions` empty state;
  `compliance-copilot` ADR-004 is the checkpointer Postgres. This plan's Phase 0 cited "ADR-004"
  meaning the former. Day 4's ADRs name the repo explicitly.
