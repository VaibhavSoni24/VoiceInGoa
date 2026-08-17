# HH Goa 2026 — Task #2: Voice-Enabled RAG Model
## Complete Build Guide + Project Description

---

## 0. Read the requirements like a rubric, not a suggestion list

Before writing code, extract every gradable requirement from the brief so nothing gets missed on a one-shot, no-resubmission submission:

| # | Requirement | What it actually means for grading |
|---|---|---|
| 1 | Voice input (real STT, not typed) | Judges will speak into your live link — mic capture must work on the first try |
| 2 | Sarvam or ElevenLabs STT (pick one) | Don't build your own ASR; wire up one vendor cleanly |
| 3 | "Vast" chunking, multiple strategies | One `chunk_size=500` split will read as minimum effort — need 2–3 strategies + justification |
| 4 | Vector DB retrieval | Real embeddings + real vector index, not `difflib` string matching |
| 5 | End-to-end latency < 200ms | STT excluded (network/audio-dependent) — the text-in → answer-out path must be sub-200ms |
| 6 | P50/P70/P100 latency numbers | Need a benchmark script and a results table/chart, not a claim |
| 7 | Harness (orchestration, retries, structured I/O, error recovery) | Not a single LLM call — a pipeline with typed stages and failure handling |
| 8 | Guardrails (off-topic, unsafe, hallucination, "don't know") | System must refuse/deflect when context doesn't support an answer |
| 9 | GitHub repo + live link + 2 videos | Deployment matters as much as code |
| 10 | #RAGInGoa on every member's IG/X/LinkedIn post | Non-negotiable — missing this flags the submission |

Since there's **no resubmission**, the guide below is written so you build once, correctly, with checkpoints to self-verify before the form is submitted.

---

## 1. Team setup (Day 0, first 2 hours)

- **Assign owners, not just tasks**: STT integration, chunking/retrieval, generation+guardrails, latency/benchmarking, frontend/live demo, video/social. 5–6 people maps to 5–6 lanes.
- **Pick the stack once, don't churn it**:
  - Backend: Python (FastAPI) — best library support for embeddings, vector DBs, and async orchestration.
  - Vector DB: **Qdrant** or **Chroma** (both run locally, both have sub-10ms ANN search at this dataset scale — good for the 200ms budget). Weaviate/Pinecone also fine if already familiar.
  - Embeddings: a small, fast multilingual model since MS MARCO-XI is Indic-language — e.g. `ai4bharat/indic-sentence-bert` or `intfloat/multilingual-e5-small`. Smaller model = lower latency, which matters more here than marginal recall gains.
  - LLM for generation: whatever you have fast API access to (Claude Haiku, GPT-4o-mini, or a local small model) — pick for **speed + JSON-mode reliability**, not raw quality.
  - STT: Sarvam (better Indic-language support given MS MARCO-XI is a Hindi/Indic dataset) or ElevenLabs (broader language support, very fast). If queries will be in Hindi/Indic languages, lean Sarvam.
- **Set up the repo skeleton immediately** (structure below) so people aren't blocked waiting on each other.

---

## 2. Dataset prep (Day 0–1)

`ai4bharat/MSMARCO-XI` is a machine-translated Indic version of MS MARCO passage-ranking data — passages + queries + relevance judgments.

1. Download a manageable slice (don't index the entire corpus if it's huge — pick a subset, e.g. 50k–200k passages, large enough to look serious, small enough to keep the index fast and load times sane).
2. Clean: strip empty passages, dedupe near-identical passages, normalize whitespace/encoding (translated corpora often have garbage tokens or broken Unicode — check for this explicitly).
3. Keep the query/relevance pairs — you'll want them later for retrieval evaluation, not just latency.

---

## 3. Chunking — this is a graded differentiator, invest here

The brief explicitly penalizes a single naive chunker. Implement **at least 3 strategies** and let your harness pick or ensemble:

1. **Fixed-size with overlap** (baseline) — e.g. 256 tokens, 20% overlap. Fast, simple, your control group.
2. **Semantic/sentence-boundary chunking** — split on sentence boundaries, then greedily pack sentences up to a token budget so no sentence is cut mid-thought. Better answer coherence.
3. **Metadata-aware chunking** — since MS MARCO passages are already short, "chunking" here can mean **passage-level indexing with metadata enrichment**: attach passage ID, source query cluster, language tag, and a short auto-generated title/summary as searchable metadata. This lets you filter/boost at retrieval time, not just embed raw text.
4. *(Optional, for extra polish)* **Hybrid retrieval**: combine dense vector search with BM25/sparse keyword search, then re-rank (reciprocal rank fusion or a cross-encoder re-ranker). This alone tends to visibly beat vector-only retrieval on MARCO-style data and is a strong "we engineered this" signal.

Log which strategy served which answer in your structured output — makes the "engineered, not naive" claim demonstrable to judges, not just asserted.

---

## 4. Retrieval + generation pipeline (the core system)

```
[Mic audio] 
   -> STT (Sarvam/ElevenLabs) 
   -> [text query]
   -> Query preprocessing (language detect, normalize)
   -> Retriever
        - embed query
        - vector search (top-k, e.g. k=8)
        - optional: sparse/BM25 search in parallel
        - fuse/re-rank -> top-n (e.g. n=3-4) context passages
   -> Guardrail check #1: is retrieval confidence high enough? (min similarity threshold)
   -> Generator (LLM call, JSON-mode, grounded-answer prompt)
   -> Guardrail check #2: is the answer grounded in the returned context? (entailment/overlap check)
   -> Guardrail check #3: off-topic/unsafe input filter (can run earlier, right after STT)
   -> [Final answer + citations back to source passages]
```

Key engineering decisions to make explicit in your writeup:
- **Top-k retrieval count** and why.
- **Similarity threshold** below which you refuse to answer ("I don't have enough grounded context to answer that").
- **Re-ranking method**, if used.

---

## 5. The harness (structured orchestration, not a raw prompt call)

Build this as an actual pipeline object with typed stages, not a script that calls an LLM once:

- **Structured I/O**: define a request/response schema (Pydantic models) for every stage — query in, retrieved chunks out, answer out. This is what "structured input/output handling" means in the brief.
- **Retries with backoff**: wrap external calls (STT API, embedding API, LLM API, vector DB) in retry logic (e.g. `tenacity` in Python) — 2–3 attempts, exponential backoff, clear failure surfaced after exhaustion.
- **Timeouts**: every external call gets a hard timeout so one slow dependency doesn't blow your 200ms budget or hang the demo.
- **Error recovery / fallback paths**: e.g., if the re-ranker times out, fall back to raw vector-search order rather than failing the whole request; if the LLM call fails, retry once then return a clear "couldn't generate an answer" rather than crashing.
- **Logging/tracing per stage**: timestamp each stage (STT done, retrieval done, generation done) — this is also how you'll produce your P50/P70/P100 numbers.

A simple way to demonstrate this well: implement it as a small state machine or pipeline class (`PipelineContext` passed through `stt_stage → retrieve_stage → guardrail_stage → generate_stage → guardrail_stage_2`), where each stage can raise a typed error the orchestrator catches and handles.

---

## 6. Guardrails — show your system knows when *not* to answer

Implement at least these, and make each one demonstrably testable in your demo video:

1. **Off-topic filter**: if the query is unrelated to the dataset domain (e.g. asking about the weather when the corpus is about something else), politely decline rather than hallucinating.
2. **Unsafe/inappropriate input handling**: basic input classification (can be a lightweight keyword+LLM-based check) that refuses harmful or inappropriate requests.
3. **Grounding/hallucination check**: after generation, verify the answer's claims are actually supported by the retrieved passages — a simple approach is asking the LLM itself, in a second short call or the same call via structured output, to cite which retrieved passage(s) support each claim, and rejecting/flagging answers with no supporting citation.
4. **Confidence-based refusal**: if top retrieval similarity is below your threshold, respond with "I don't have enough information to answer that confidently" instead of forcing an answer.

Judges will likely test this by asking something the corpus can't answer — make sure that path is a first-class, tested feature, not an afterthought.

---

## 7. Latency engineering + benchmarking

**Target: sub-200ms for chunking + retrieval + generation** (STT itself is network/audio bound and reasonably excluded from this number, but be ready to explain that clearly).

To hit 200ms:
- Use a **small, fast embedding model** and keep it warm in memory (no cold-start reload per request).
- Use an **in-memory or locally-hosted vector DB** — network hops to a remote hosted vector DB add latency you don't need.
- Keep **top-k small** (retrieval of 5–10 candidates, not 100).
- Use a **fast LLM** for generation, and keep prompts short — long system prompts and long retrieved context both add latency.
- **Parallelize** independent stages (e.g. sparse + dense search) with `asyncio`/threads instead of running sequentially.
- **Cache** embeddings for repeated/common queries if relevant.

**Benchmarking script**: run 100+ representative queries (sample real ones from the MARCO query set) through the retrieval+generation path, record per-stage and total latency, then compute:
- P50 (median)
- P70
- P100 (worst case — don't cherry-pick, report your actual max)

Present this as a small table or chart in your README and demo video — this is one of the most concretely gradable parts of the rubric, so don't skip presenting it clearly.

---

## 8. Repo structure (suggested)

```
voice-rag-hhgoa/
├── README.md                 # project description (see template below)
├── data/
│   ├── prepare_dataset.py    # download + clean MSMARCO-XI subset
├── src/
│   ├── stt/                  # Sarvam/ElevenLabs client wrapper
│   ├── chunking/              # 3+ chunking strategies
│   ├── retrieval/             # embedding, vector DB client, hybrid search, re-ranker
│   ├── generation/             # LLM prompt + structured output schema
│   ├── guardrails/             # off-topic, unsafe, grounding checks
│   ├── pipeline/               # harness: orchestrator, retries, error recovery
│   └── api/                    # FastAPI app (voice upload -> answer endpoint)
├── frontend/                   # minimal mic-capture UI -> calls API
├── benchmarks/
│   ├── run_latency_bench.py
│   └── results/               # P50/P70/P100 output, charts
├── tests/
├── videos/                    # or links in README
└── requirements.txt / pyproject.toml
```

---

## 9. Frontend / live link

Keep it minimal but working reliably live:
- A single page: mic button → record → send audio → show transcribed query → show streaming/loading state → show grounded answer with cited source passage(s).
- Show the retrieval sources and latency numbers **on screen** — this doubles as a live demo of your engineering rigor, not just the answer.
- Deploy somewhere stable (Render, Railway, Fly.io, or a VM) — test the live link from a fresh browser/incognito session before submitting, since judges will hit the real deployed link, not your laptop.

---

## 10. Testing pass before submission (do this as a team, out loud)

- [ ] Speak 5 different real questions into the live link — all transcribe and answer correctly.
- [ ] Speak 1 off-topic question — system correctly refuses.
- [ ] Speak 1 nonsense/unsafe input — guardrail catches it.
- [ ] Latency numbers on screen match your benchmark script's output.
- [ ] Pipeline survives one forced failure (kill network briefly, or point to a bad API key) without crashing — recovers or fails gracefully.
- [ ] GitHub repo is public, README complete, code runs from a clean clone.
- [ ] Live link works from an incognito window / different device.
- [ ] Both videos recorded (Team/process ≤90s, Demo video) and uploaded to Instagram, X, and LinkedIn **by every team member individually**.
- [ ] Every single post includes **#RAGInGoa**, and at least one IG account among the team is public.
- [ ] Submission form filled once, carefully — repo link, live link, video links, confirmation phrase.

---

# Project Description Template (for your README / submission form)

> Copy this, fill in the brackets, and adjust the specifics to what you actually built.

---

## [Project Name] — Voice-Enabled RAG for Indic Question Answering

**One-line pitch:** A sub-200ms, guardrailed voice-to-answer retrieval system built on the MS MARCO-XI Indic dataset — speak a question, get a grounded, cited answer, or a clear refusal when the system isn't confident.

### Problem & Approach
Most RAG demos stop at "chunk, embed, retrieve, generate." We treated retrieval quality, latency, and answer safety as first-class engineering problems, not afterthoughts. [Team name] built a full voice-to-answer pipeline that transcribes spoken Indic-language queries, retrieves grounded context from MS MARCO-XI using [N] complementary chunking/retrieval strategies, and generates cited, guardrailed answers — all orchestrated through a structured pipeline with retries and error recovery, benchmarked end-to-end at P50 [X]ms / P70 [X]ms / P100 [X]ms.

### Architecture
Voice input → [Sarvam/ElevenLabs] STT → query preprocessing → hybrid retrieval ([dense embedding model] + [sparse/BM25], re-ranked via [method]) → grounding-confidence check → [LLM] generation with structured, cited output → hallucination/grounding guardrail → final spoken-question-answered response with source citations.

### What makes the retrieval "engineered, not naive"
We implemented and A/B'd three chunking strategies — fixed-size overlap, sentence-boundary semantic chunking, and metadata-enriched passage indexing — and combined dense + sparse retrieval with [re-ranking method], because [brief reasoning, e.g. "MS MARCO-XI's short, translated passages meant naive fixed chunking lost cross-passage context that metadata linking recovered"].

### Latency engineering
To hit the sub-200ms target we [kept the embedding model warm in-process / used an in-memory vector index / capped top-k at N / parallelized dense+sparse search / used a fast small LLM], measured across [N] real queries sampled from the MARCO query set.

| Metric | Latency |
|---|---|
| P50 | [X] ms |
| P70 | [X] ms |
| P100 | [X] ms |

### Harness & reliability
The pipeline runs through a typed orchestrator (`[module/class name]`) with structured request/response schemas at every stage, retry-with-backoff on all external calls (STT, embedding, LLM, vector DB), hard timeouts, and explicit fallback paths (e.g. [re-ranker timeout → fall back to raw vector order]) — so a single slow or failing dependency degrades gracefully instead of crashing the request.

### Guardrails
The system refuses to answer when retrieval confidence falls below [threshold], filters off-topic and unsafe queries before they reach generation, and checks generated answers for grounding against the retrieved passages before returning them — surfaced transparently in the UI as [cited sources / confidence score / refusal message].

### Tech stack
STT: [Sarvam/ElevenLabs] · Embeddings: [model] · Vector DB: [Qdrant/Chroma/etc.] · LLM: [model] · Backend: [FastAPI] · Frontend: [stack] · Deployment: [platform]

### Links
- GitHub: [repo link]
- Live demo: [live link]
- Team/process video: [link]
- Demo video: [link]

#RAGInGoa

---

## Final notes on the meta-requirements from the announcement

- **No resubmission, one submission per team** — assign one person as the final "submit owner" so the form isn't accidentally submitted twice by different members.
- **No leaderboard this round** — judging is on engineering depth, project execution, presentation, and teamwork, so weight your time toward the harness, guardrails, and latency benchmarking sections above; these are the parts a "naive RAG demo" skips and where this round is explicitly evaluating you.
- **Confirmation phrase field** on the form exists to prove you read the instructions — copy it exactly as shown, don't paraphrase it.
- **Social posts**: schedule these *before* the deadline crunch — every member, every platform, every post tagged `#RAGInGoa`, at least one public Instagram account on the team.