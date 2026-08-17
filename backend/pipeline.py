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
            "refused": True,
            "content": "I cannot answer this request as it violates safety policies.",
            "reason": "Unsafe input detected",
            "metrics": {"total_rag_ms": int((time.time() - start_time) * 1000)}
        }

    # 2. Retrieval
    retrieved_docs, retrieval_ms = retrieve(query, top_k=3)
    
    # 3. Guardrail Check: Retrieval Confidence
    if not Guardrails.check_retrieval_confidence(retrieved_docs):
        return {
            "refused": True,
            "content": "I don't have enough grounded information to answer that confidently.",
            "reason": "Low retrieval confidence",
            "metrics": {
                "retrieval_ms": retrieval_ms,
                "total_rag_ms": int((time.time() - start_time) * 1000)
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
    
    citations = [{"id": doc["parent_id"], "text": doc["text"]} for doc in retrieved_docs]
    
    total_rag_ms = int((time.time() - start_time) * 1000)
    
    return {
        "refused": False,
        "content": answer_text,
        "citations": citations,
        "metrics": {
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "total_rag_ms": total_rag_ms
        }
    }
