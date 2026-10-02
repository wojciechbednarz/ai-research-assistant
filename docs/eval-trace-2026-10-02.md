# Eval trace — faithfulness, on paper (2026-10-02)

---

## 1. Row schema

| Field | Type | What it holds |
|---|---|---|
| `question` | `str` | User question/query presenting the input for the retrieval system |
| `retrieved_context` | `list[dict]` | Documents searched in the vector database, that are most relevanty to the user query (hybrid search semantic + keyword matching) |
| `generated_answer` | `str` | Answer captured from a real run. LLM do analysis, produces dictionary and in the endpoint we take "answer" key, getting the answer as string |
| `reference_answer` | ? | Dont include, this is not related to Faithfulness but rather to Context Recall or answer correctness |

**`retrieved_context` item:** `{"id": id_, "document": doc, "distance": dist}`
- from it i need "document" - to judge about context and "id" - as identifier for supported/unsupporter claims, distance is not needed for faithfulness

| Key | Decision |
|---|---|
| `id` | keep |
| `document` | keep |
| `distance` | drop |

---

## 2. Faithfulness definition

**Claim-splitting rule:**
1. SPlit the answer into sentences
2. In each sentence split at "and" - each aprt becomes one claim
3. Replace "it" with the thing it refers to, so each claim makes sense alone

**Applied:**
- RAG is a retrieval system for AI systems. -> No "and" so it stays as one claim -> C1
  - **C1** - RAG is a retrieval system for AI systems
- RAG is a retrieval system and it was invented in 2020. -> "and" present so its split in two - C2 and C3.
  - **C2** - RAG is a retrieval system
  - **C3** - RAG was invented in 2020

**One-line context:** RAG combines a retriever with a generator to ground LLM answers in documents.

**Checked against the context:**

| Claim | Mark | Why |
|---|---|---|
| **C1** - RAG is a retrieval system for AI systems | U | says about retrieving but not about AI systems. |
| **C2** - RAG is a retrieval system | S | says about retreiving. |
| **C3** - RAG was invented in 2020 | U | doesnt say about invention of RAG. |

**Score (sentence 2 — the discriminating row):** C2=S, C3=U → 1 / 2 = **0.5**
- Fluent, on-topic answer with one unsupported claim scores < 1.0, so the definition passes the discriminating check.

---

## 3. The judge prompt

A claim is supported if the retrieved context states it or directly implies it —
you could prove the claim true using only the context. Shared words are not enough;
a claim the context contradicts or never mentions is unsupported.

The judge receives: the retrieved context + the generated answer.
The judge returns ONLY this JSON, nothing else:
[{"claim": "<one claim, pronouns replaced>", "mark": "S" | "U"}, ...]
Splitting rule for the judge: one fact per claim; split at "and"; replace "it"/"this" with what it refers to.

---

## 4. One traced row

**Question:** What is RAG?

**Retrieved context (hybrid_search, top 3):**
- rag_chunk0 — "RAG (Retrieval-Augmented Generation). Connecting LLMs with external knowledge
  sources so they can answer questions and take actions based on specific data, not just training knowledge."
- chromadb-vector-database_chunk4 — "...and retrieved docs to LLM as context. Lets the LLM answer using
  data outside its training set. Caveat: "similar" ≠ "relevant"; retrieval quality is subjective..."
- chromadb-vector-database_chunk0 — Real Python ChromaDB tutorial intro: vectors, embeddings, cosine similarity.

**Generated answer:** (the API's "answer" string)

**Claims (rule: sentences → split at "and" → replace "This"/"It" with RAG):**

| # | Claim | Mark | Evidence |
|---|---|---|---|
| C1 | RAG stands for Retrieval-Augmented Generation | S | rag_chunk0 title |
| C2 | RAG is a technique that connects LLMs with external knowledge sources | S | rag_chunk0 |
| C3 | RAG allows LLMs to answer questions based on specific data | S | rag_chunk0 |
| C4 | RAG allows LLMs to perform actions based on specific data | S | rag_chunk0 "take actions" |
| C5 | RAG goes beyond the LLM's training knowledge | S | rag_chunk0 "not just training knowledge" |
| C6 | RAG works by retrieving **relevant** documents | S ⚠️ | chunk4 says docs are retrieved — but also warns "similar ≠ relevant" |
| C7 | RAG provides the retrieved documents to the LLM as context | S | chunk4 |
| C8 | RAG lets the LLM use information outside its training set | S | chunk4 |

**Score:** 8 / 8 = **1.0** (7 / 8 = 0.875 if C6 is marked U)
