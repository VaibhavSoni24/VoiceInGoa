import json
from typing import List, Dict

# Chunking Strategy 1: Fixed-size with overlap
def chunk_fixed_size(text: str, chunk_size=200, overlap=50) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

# Chunking Strategy 2: Semantic (sentence boundaries)
def chunk_semantic(text: str, max_words=150) -> List[str]:
    # Very basic sentence boundary detection for English/Indic text
    sentences = text.replace('?', '.').replace('!', '.').replace('।', '.').split('.')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        words = sentence.split()
        if current_length + len(words) > max_words and current_chunk:
            chunks.append(" ".join(current_chunk) + ".")
            current_chunk = [sentence]
            current_length = len(words)
        else:
            current_chunk.append(sentence)
            current_length += len(words)
            
    if current_chunk:
        chunks.append(" ".join(current_chunk) + ".")
        
    return chunks

# Strategy 3: Metadata-aware chunking wrapper
def apply_chunking_strategies(passage: Dict) -> List[Dict]:
    text = passage.get("text", "")
    pid = passage.get("_id", "unknown")
    
    # We will use the semantic strategy as the primary one for quality
    text_chunks = chunk_semantic(text)
    
    result = []
    for idx, chunk in enumerate(text_chunks):
        result.append({
            "id": f"{pid}_{idx}",
            "parent_id": pid,
            "text": chunk,
            "chunk_idx": idx,
            "strategy": "semantic",
            "metadata_rich_text": f"Source passage {pid}: {chunk}" # Prepended metadata for better embedding
        })
        
    return result
