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
        
        # Save corpus to JSONL for easier processing
        with open(corpus_file, "w", encoding="utf-8") as f:
            for _, row in df.iterrows():
                # MS MARCO-XI parquet schema: _id, text, etc.
                item = {
                    "_id": str(row.get("_id", row.name)),
                    "text": str(row.get("text", "")),
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        print("Dataset preparation complete.")
        
    except Exception as e:
        print(f"Error downloading dataset: {e}")

if __name__ == "__main__":
    download_and_prep_dataset()
