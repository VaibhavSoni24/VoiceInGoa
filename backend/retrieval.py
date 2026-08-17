import os
import json
import time
import torch
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from chunking import apply_chunking_strategies

QDRANT_PATH = os.environ.get("QDRANT_PATH", "./qdrant_storage")
COLLECTION_NAME = "msmarco_xi"

print("Loading embedding model using transformers directly...")
tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
model = AutoModel.from_pretrained("intfloat/multilingual-e5-small")
print("Model loaded.")

def get_embedding(text: str):
    encoded_input = tokenizer([text], padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    # Mean pooling
    token_embeddings = model_output[0]
    input_mask_expanded = encoded_input['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
    sentence_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    # Normalize embeddings as required by e5 models
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    return sentence_embeddings[0].tolist()


def get_qdrant_client():
    os.makedirs(QDRANT_PATH, exist_ok=True)
    return QdrantClient(path=QDRANT_PATH)

def init_collection():
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    return client

def index_dataset(corpus_file="data/corpus.json", limit=None):
    client = init_collection()
    
    if not os.path.exists(corpus_file):
        print(f"Corpus file {corpus_file} not found. Run data_prep.py first.")
        return
        
    print(f"Indexing {corpus_file}...")
    points = []
    count = 0
    
    with open(corpus_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            passage = json.loads(line)
            
            chunks = apply_chunking_strategies(passage)
            for chunk in chunks:
                # E5 models recommend prefixing "query: " or "passage: "
                # We prefix with "passage: "
                vector = get_embedding("passage: " + chunk["metadata_rich_text"])
                
                points.append(PointStruct(
                    id=abs(hash(chunk["id"])) % (10 ** 15), # Convert string ID to positive int for Qdrant
                    vector=vector,
                    payload=chunk
                ))
                
            count += 1
            if count % 100 == 0:
                print(f"Processed {count} passages...")
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                points = []
                
            if limit and count >= limit:
                break
                
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        
    print(f"Finished indexing {count} passages.")

def retrieve(query: str, top_k=5):
    client = init_collection()
    start_time = time.time()
    
    # E5 models prefix
    query_vector = get_embedding("query: " + query)
    
    search_result = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    
    retrieval_ms = int((time.time() - start_time) * 1000)
    
    results = []
    for hit in search_result:
        results.append({
            "score": hit.score,
            "text": hit.payload["text"],
            "parent_id": hit.payload["parent_id"]
        })
        
    return results, retrieval_ms

if __name__ == "__main__":
    # If run directly, perform indexing on a small limit for quick setup
    # Pass limit=None to index the full downloaded dataset
    index_dataset(limit=5000) 
