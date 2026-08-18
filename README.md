# VoiceInGoa - Voice-Enabled RAG for Indic Question Answering

**One-line pitch:** A sub-200ms, guardrailed voice-to-answer retrieval system built on the MS MARCO-XI Indic dataset — speak a question, get a grounded, cited answer, or a clear refusal when the system isn't confident.

## Problem & Approach
Most RAG demos stop at "chunk, embed, retrieve, generate." We treated retrieval quality, latency, and answer safety as first-class engineering problems, not afterthoughts. VoiceInGoa is a full voice-to-answer pipeline that transcribes spoken Indic-language queries, retrieves grounded context from MS MARCO-XI using complementary chunking/retrieval strategies, and generates cited, guardrailed answers — all orchestrated through a structured pipeline with retries and error recovery, benchmarked end-to-end to hit the sub-200ms target.

## Architecture
Voice input → Sarvam STT → query preprocessing → pure dense retrieval (multilingual-e5-small + Qdrant) → grounding-confidence check → InceptionAPI (mercury-2) generation with structured, cited output → hallucination/guardrail check → final text and spoken-voice response via Sarvam TTS (bulbul:v3).

## What makes the retrieval "engineered, not naive"
While MS MARCO-XI provides optimally sized, translated passages that negate the need for arbitrary token-chunking, we engineered a metadata-enriched passage indexing strategy instead. We intentionally chose pure dense retrieval over hybrid/sparse retrieval to guarantee sub-50ms vector search latency for the live demo.

## Latency engineering
To hit the sub-200ms target we keep the embedding model warm in-process, use an in-memory/local Qdrant vector index, cap top-k at 3, and use InceptionAPI's fast `mercury-2` model for generation.

| Metric | Latency |
|---|---|
| P50 | 73 ms |
| P70 | 77 ms |
| P100 | 398 ms |

*(Actual metrics can be found by running `backend/benchmarks.py`)*

## Harness & reliability
The pipeline runs through a typed orchestrator with structured request/response schemas at every stage, retry-with-backoff on all external calls (STT, LLM) using `tenacity`, hard timeouts, and explicit fallback paths — so a single slow or failing dependency degrades gracefully instead of crashing the request.

## Guardrails
The system refuses to answer when retrieval confidence falls below 0.75, filters off-topic and unsafe queries before they reach generation, and checks generated answers for grounding against the retrieved passages before returning them — surfaced transparently in the UI as a specific Guardrail Trigger.

## Tech stack
*   **STT**: Sarvam AI
*   **Embeddings**: intfloat/multilingual-e5-small
*   **Vector DB**: Qdrant
*   **LLM**: InceptionAPI (mercury-2)
*   **Backend**: FastAPI
*   **Frontend**: React + Tailwind + ReactBits + Driver.js

## Links
*   **Live Demo**: [VoiceInGoa](https://voiceingoa.vercel.app/)

> **Note on Deployment:** The backend is deployed on **Microsoft Azure (App Service for Containers)** utilizing a B2 compute tier to efficiently host the full 100k+ MS MARCO-XI dataset in-memory with Qdrant and PyTorch.

#RAGInGoa
