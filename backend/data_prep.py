import os
import json
import pandas as pd
import requests

def download_and_prep_dataset(output_dir="data"):
    print("Downloading MSMARCO-XI dataset (Validation/Hindi)...")
    os.makedirs(output_dir, exist_ok=True)
    
    parquet_url = "https://huggingface.co/datasets/ai4bharat/MSMARCO-XI/resolve/main/validation/hinval.parquet"
    parquet_file = os.path.join(output_dir, "hinval.parquet")
    corpus_file = os.path.join(output_dir, "corpus.json")
    
    try:
        # Download the parquet file directly using requests to bypass datasets/pyarrow errors
        print(f"Fetching from {parquet_url}...")
        response = requests.get(parquet_url, stream=True)
        response.raise_for_status()
        
        with open(parquet_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print("Download complete. Reading with fastparquet...")
        # Read the parquet file
        df = pd.read_parquet(parquet_file, engine='fastparquet')
        
        print(f"Loaded {len(df)} passages. Saving to {corpus_file}...")
        
        with open(corpus_file, "w", encoding="utf-8") as f:
            # Prepend Golden Records
            if os.path.exists("golden_records.json"):
                with open("golden_records.json", "r", encoding="utf-8") as gf:
                    golden = json.load(gf)
                    for i, record in enumerate(golden):
                        f.write(json.dumps({"_id": f"golden_{i}", "text": record}, ensure_ascii=False) + "\n")
            
            count = 0
            for _, row in df.iterrows():
                query_id = str(row.get("query_id", row.name))
                passages = row.get("passages.Translated_passages", [])
                
                if passages is None or not isinstance(passages, (list, tuple)) and not hasattr(passages, "__iter__"):
                    continue
                    
                for i, p in enumerate(passages):
                    if not p: continue
                    item = {
                        "_id": f"{query_id}_{i}",
                        "text": str(p),
                    }
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    count += 1
                
        print(f"Dataset preparation complete. Wrote {count} passages + golden records.")
        
    except Exception as e:
        print(f"Error downloading dataset: {e}")

if __name__ == "__main__":
    download_and_prep_dataset()
