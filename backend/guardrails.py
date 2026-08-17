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
