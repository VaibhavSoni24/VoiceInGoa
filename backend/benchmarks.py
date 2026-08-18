import time
import statistics
from pipeline import run_rag_pipeline

def run_benchmarks():
    test_queries = [
        "what is the capital of india?",
        "how to cook pasta?",
        "who won the world cup in 2011?",
        "what are the symptoms of covid-19?",
        "tell me about ms marco dataset"
    ]
    
    print(f"Running benchmarks over {len(test_queries)} queries...")
    latencies = []
    
    for i, query in enumerate(test_queries):
        print(f"Query {i+1}: {query}")
        result = run_rag_pipeline(query)
        rag_ms = result["latency_ms"]["total"]
        print(f" -> Latency: {rag_ms} ms")
        latencies.append(rag_ms)
        
    latencies.sort()
    
    p50 = statistics.median(latencies)
    p70 = latencies[int(len(latencies) * 0.70)]
    p100 = max(latencies)
    
    print("\n--- Benchmark Results ---")
    print(f"P50:  {p50:.2f} ms")
    print(f"P70:  {p70:.2f} ms")
    print(f"P100: {p100:.2f} ms")
    print("-------------------------")
    
if __name__ == "__main__":
    run_benchmarks()
