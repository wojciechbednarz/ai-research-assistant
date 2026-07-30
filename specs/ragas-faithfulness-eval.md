# Spec: RAGAS Faithfulness Eval

- **Status:** Draft / MVP
- **Tracking:** `ai-research-assistant#5`
- **Governing plan:** `learning-helper-claude-proj/MASTER_PLAN.md` (C1W8, Roche interview prep week)
- **Branch:** `feat/ragas-faithfulness-eval`
- **Date:** 2026-07-17

> This is a **design spec**, not implementation. No code is written here.
> **Lane 1 constraint:** the developer (Wojciech) writes 100% of the code. An advisor may point at
> RAGAS docs and critique the golden-set design — nothing more.

---

## 1. Purpose

Add an offline evaluation harness that scores the **faithfulness** of the research assistant's
answers — i.e. what fraction of the claims in a generated answer are actually grounded in the
retrieved context.

Two intents, in priority order:

1. **Interview artifact** (primary, this week). Concrete proof for the Roche *Technical Development
   Lead (GenAI)* interview: *"I trace **and** score."* Turns the repo's existing "anti-hallucination
   as a feature" narrative from an assertion into a number.
2. **Learning** (secondary). Deliberate practice with LLM-as-judge evaluation, async judge calls,
   and the offline-batch-metric mental model.

Non-goal: a production evaluation platform. This is a minimal, honest first cut.

---

## 2. Background: what faithfulness measures

RAGAS `Faithfulness` is a **reference-free** metric. It needs **no ground-truth answer**.

The judge LLM runs two passes:
1. Decompose the generated `answer` into atomic factual claims.
2. For each claim, check whether the `retrieved_contexts` support it.

```
faithfulness = supported_claims / total_claims   ∈ [0, 1]
```

- `1.0` — every statement traces back to a retrieved chunk.
- Low — the model asserted things retrieval never provided (hallucination beyond context).

**Consequence for the test set:** because no human "correct answer" is required, the eval set is not
hand-authored Q&A pairs — it is **recordings of real pipeline runs**: the triple
`(question, retrieved_contexts, answer)` that the pipeline already produces on every request.

---

## 3. The one wiring fact that matters

The pipeline exposes two different things; only one is the correct context source.

| Field | Where | What it is | Use for RAGAS? |
|---|---|---|---|
| `RespondResponse.sources` | `schemas.py` | short titles / snippets shown to the user | ❌ No |
| `AgentState["documents"]` | `agent/graph.py` | list of `{id, document, distance, hybrid_score}` — `document` is the **full retrieved chunk text** | ✅ Yes |

`retrieved_contexts` **must** be built from `state["documents"][i]["document"]`, **not** from `sources`.
Scoring against `sources` (a few short titles) would make almost every real claim look unsupported and
produce a meaningless low score.

> The current `evals.py` is fully mocked (`mocked_llm_context()` returns fake strings), so it has never
> had to confront this. Replacing the mock with the real `documents` field is the core of the MVP.

---

## 4. Approach (chosen: capture → fixture → score)

Split the work into two commands rather than scoring off a live run each time.

```
capture:  run_graph over N questions  ->  writes evals/golden_set.json
score:    reads golden_set.json        ->  runs Faithfulness  ->  prints per-row + mean
```

**Why split:**

- **Determinism / cheapness.** Scoring reads a frozen JSON file. Re-score, tweak thresholds, or add a
  metric without re-invoking the agent or needing ChromaDB running. The expensive, flaky part (running
  the agent + LLM) happens once.
- **Correct mental model.** RAGAS is an *offline, batch* metric library — you evaluate a dataset, not a
  live request. (Contrast: TruLens = live instrumentation + feedback functions.) The split makes that
  explicit and is directly interview-relevant.
- **Clean upgrade path.** The fixture is exactly what a future CI gate or Langfuse-logging step would
  consume — neither of which is built this week.

**Rejected alternatives:**

- *Live run-and-score every time* — couples judge to a running pipeline + vector store; slow;
  non-deterministic scores. Fine for a one-off, bad as a repeatable eval.
- *Hand-authored golden set* — fake contexts measure a fiction; violates the "real repo" intent.

---

## 5. Golden set

- **Location:** `evals/golden_set.json`
- **Size:** 5-8 rows.
- **Row shape:**

```
{
  "question":           str,
  "retrieved_contexts": list[str],   // from documents[i]["document"]
  "answer":             str,
  "notes":              str          // e.g. "grounded / high", "refusal case"
}
```

**Composition:**
- ≥3 grounded queries expected to score high (e.g. `"What is function calling"` against the Polish
  AI corpus).
- ≥2 **refusal cases** (`confidence: low`, empty sources — e.g. `"What is quantum computing"`). An
  honest refusal makes no unsupported claims, so faithfulness should score **high**. This both
  demonstrates the metric rewarding restraint and forces the harness to handle the empty-context path.

---

## 6. Harness

Two functions, no framework, replacing the mocked scaffolding in `evals.py`.

- `capture(questions: list[str]) -> None`
  - Runs `run_graph` per question.
  - Writes `{question, contexts=[d["document"] for d in result["documents"]], answer=result["answer"]}`
    to `evals/golden_set.json`.
  - Requires a seeded ChromaDB collection.
- `score(fixture_path: str) -> None`
  - Loads the fixture.
  - For each row builds a RAGAS `SingleTurnSample(user_input, response, retrieved_contexts)`.
  - Scores with `Faithfulness(llm=judge_llm)` — the existing `LangchainLLMWrapper` over OpenRouter.
  - Prints per-row score + mean.

Both stay `async` (judge calls are async — reuse the existing `single_turn_ascore` path).

---

## 7. Scope caps (from MASTER_PLAN C1W8)

**This week's done-state:** RAGAS installed, golden set drafted, **≥1 row scored and printed.**

**Overflow (Sun/Mon optional, ranked below mock interviews):** full 5-8 rows scored + scores logged
into Langfuse alongside existing traces.

**Explicitly out of scope:**
- ❌ CI gate / release threshold
- ❌ dashboard
- ❌ new endpoints / features
- ❌ refactoring the RAG pipeline "while I'm in there"
- ❌ a new chatbot (the assistant *is* the chatbot — a fresh build was considered and rejected Jul 16)

**Cut rule:** this build is the **first** thing cut if any core prep item (PII/OAuth2 drill, STARs,
walkthrough, mocks) is behind. Never the reverse.

---

## 8. Interview-defensibility (Roche artifact)

**Metric definitions to speak cold:**
- **Faithfulness** — answer claims supported by retrieved context (groundedness). Reference-free.
- **Answer relevancy** — does the answer address the question (not off-topic / padded).
- **Context precision** — of the retrieved chunks, how many are relevant (retrieval noise).
- **Context recall** — of the relevant chunks that exist, how many were retrieved (retrieval coverage;
  needs a reference).

**RAGAS vs TruLens (when-which):**
- RAGAS = offline / CI batch metric library.
- TruLens = live instrumentation + feedback functions (the "RAG triad": context relevance,
  groundedness, answer relevance).
- Both are LLM-as-judge → **validate against human labels** before trusting the number.

**Honesty caveats to state proactively** (technical-conscience signal):
- Code is a **4-node** graph (retrieve → analyze → approve → respond), not the README's 3.
- `/research/stream` is **stubbed**, not implemented.
- Only **2** tools are actually MCP-registered, not 3.
- **No** eval-in-CI, auth, PII masking, or AWS in this repo.

---

## 9. Learning hooks

- **Async judge calls** — `single_turn_ascore`; batching / concurrency considerations for larger sets.
- **LLM-as-judge validation** — a judge score is itself a model output; it must be checked against a
  small human-labeled set before being trusted.
- **Offline batch vs live instrumentation** — RAGAS vs TruLens as a design axis.
- **Determinism** — LLM judges are non-deterministic; the capture/score split isolates that variance to
  the score step.

---

## 10. Risks

- **Weak / biased judge.** The judge (Gemini Flash Lite via OpenRouter) is the same cheap model family
  that generates the answers. A weak judge yields noisy faithfulness scores; a same-family judge can be
  biased toward its own outputs. Acceptable this week (demonstrating the *mechanism*, not publishing a
  benchmark) — but name it, and have the fix ready: a stronger, independent judge model + a small
  human-labeled validation set. Stating this out loud is worth more than a clean number.
- **Fixture staleness.** The golden set is a snapshot; it drifts when the corpus, prompts, or retrieval
  change. Re-capture when the pipeline changes. Acceptable for an offline eval.
- **ChromaDB dependency for capture.** `capture` needs a seeded collection running; `score` does not.

---

## 11. Open questions

1. Add `answer_relevancy` in the first pass, or faithfulness-only until it's clean?
2. Golden-set language mix — English queries, Polish queries, or both (corpus is Polish)?
3. Langfuse logging in this branch, or a follow-up once ≥1 row scores?
4. Post-hire: does this harness graduate into a real eval-in-CI gate, or stay a manual artifact?
