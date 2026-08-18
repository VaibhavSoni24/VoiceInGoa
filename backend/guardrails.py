from typing import List, Dict, Any

class Guardrails:
    CONFIDENCE_THRESHOLD = 0.75

    @staticmethod
    def check_retrieval_confidence(retrieved_docs: List[Dict]) -> bool:
        if not retrieved_docs:
            return False
        # If the top result score is too low, we refuse to answer to prevent hallucination
        top_score = retrieved_docs[0].get("score", 0)
        return top_score >= Guardrails.CONFIDENCE_THRESHOLD

    @staticmethod
    def is_safe_input(query: str) -> bool:
        # Basic keyword-based safety check (in a real scenario, could use an LLM or classifier)
        unsafe_keywords = ["bomb", "hack", "kill", "illegal", "suicide"]
        query_lower = query.lower()
        if any(kw in query_lower for kw in unsafe_keywords):
            return False
        return True

    @staticmethod
    def is_on_topic(query: str) -> bool:
        # Could use a fast LLM classification, but for latency, we assume it's on topic 
        # unless retrieval fails the confidence check.
        return True

    @staticmethod
    def post_generation_check(answer: str, context: str) -> bool:
        import os
        import requests
        
        inception_key = os.environ.get("INCEPTION_API_KEY", "")
        if not inception_key:
            return True # Skip if no key
            
        url = "https://api.inceptionlabs.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {inception_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"Context:\n{context}\n\nAnswer to verify:\n{answer}\n\nDoes the answer contain any specific claims or facts that are NOT supported by the context? Reply strictly with 'TRUE' if it contains unsupported claims (hallucination), or 'FALSE' if it is fully supported."
        
        payload = {
            "model": "mercury-2",
            "reasoning_effort": "low",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=3)
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"].strip().upper()
                if "TRUE" in result:
                    return False # Grounding failed (unsupported claims found)
            return True # Grounding passed
        except Exception:
            # Default to passing if the verification API fails to maintain availability
            return True
