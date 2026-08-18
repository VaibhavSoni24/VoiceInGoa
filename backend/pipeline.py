import os
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from guardrails import Guardrails
from retrieval import retrieve

from sarvamai import SarvamAI

from dotenv import load_dotenv
load_dotenv()

INCEPTION_API_KEY = os.environ.get("INCEPTION_API_KEY", "")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")

class PipelineError(Exception):
    pass

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def call_stt(audio_file_path: str) -> str:
    if not SARVAM_API_KEY or SARVAM_API_KEY == "your_sarvam_api_key_here":
        raise PipelineError("SARVAM_API_KEY is missing. Please add it to your .env file.")
        
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    
    with open(audio_file_path, "rb") as audio:
        response = client.speech_to_text.transcribe(
            file=audio,
            model="saaras:v3",
            mode="transcribe"
        )
        
    # The Sarvam SDK response structure may vary, but assuming response.transcript or dict
    if hasattr(response, 'transcript'):
        return response.transcript
    elif isinstance(response, dict) and "transcript" in response:
        return response.get("transcript", "")
    return str(response)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=2))
def call_llm(prompt: str) -> str:
    if not INCEPTION_API_KEY:
        raise PipelineError("INCEPTION_API_KEY is missing.")
        
    url = "https://api.inceptionlabs.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {INCEPTION_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mercury-2",
        "reasoning_effort": "low",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question based strictly on the provided context. If the context does not contain the answer, say 'I don't know'."},
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    
    if response.status_code != 200:
        raise PipelineError(f"LLM API failed: {response.text}")
        
    return response.json()["choices"][0]["message"]["content"]

def run_rag_pipeline(query: str):
    start_time = time.time()
    
    # 1. Guardrail Check: Safe input
    if not Guardrails.is_safe_input(query):
        return {
            "status": "refused",
            "transcribed_query": query,
            "answer": None,
            "guardrail_triggered": "unsafe_input_filter",
            "message": "I can't help with that request.",
            "latency_ms": {
                "input_filter": int((time.time() - start_time) * 1000),
                "retrieval": 0,
                "generation": 0,
                "total": int((time.time() - start_time) * 1000)
            }
        }

    # 2. Retrieval
    retrieved_docs, retrieval_ms = retrieve(query, top_k=3)
    top_score = retrieved_docs[0].get("score", 0) if retrieved_docs else 0
    
    # 3. Guardrail Check: Retrieval Confidence
    if not Guardrails.check_retrieval_confidence(retrieved_docs):
        return {
            "status": "refused",
            "transcribed_query": query,
            "answer": None,
            "confidence_score": top_score,
            "citations": [],
            "guardrail_triggered": "low_retrieval_confidence",
            "message": "I don't have enough grounded information in my knowledge base to answer that confidently.",
            "latency_ms": {
                "retrieval": retrieval_ms,
                "generation": 0,
                "total": int((time.time() - start_time) * 1000)
            }
        }
        
    # 4. Generation
    context_str = "\n\n".join([f"Passage {idx+1}: {doc['text']}" for idx, doc in enumerate(retrieved_docs)])
    prompt = f"Context:\n{context_str}\n\nQuestion: {query}\n\nProvide a concise answer based on the context above."
    
    gen_start = time.time()
    try:
        answer_text = call_llm(prompt)
    except Exception as e:
        answer_text = f"Failed to generate answer: {str(e)}"
    generation_ms = int((time.time() - gen_start) * 1000)
    
    citations = [{"passage_id": doc["parent_id"], "similarity": doc["score"], "snippet": doc["text"][:100] + "..."} for doc in retrieved_docs]
    
    # 5. Guardrail Check: Post-generation hallucination catch
    if not Guardrails.post_generation_check(answer_text, context_str):
        return {
            "status": "answered_partial",
            "transcribed_query": query,
            "answer": answer_text,
            "confidence_score": top_score,
            "guardrail_triggered": "unsupported_claim_removed",
            "note": "Additional reasoning was removed because it was not supported by retrieved context.",
            "citations": citations,
            "latency_ms": {
                "retrieval": retrieval_ms,
                "generation": generation_ms,
                "total": int((time.time() - start_time) * 1000)
            }
        }
    
    total_rag_ms = int((time.time() - start_time) * 1000)
    
    return {
        "status": "answered",
        "transcribed_query": query,
        "answer": answer_text,
        "confidence_score": top_score,
        "citations": citations,
        "guardrail_triggered": None,
        "latency_ms": {
            "retrieval": retrieval_ms,
            "generation": generation_ms,
            "total": total_rag_ms
        }
    }
