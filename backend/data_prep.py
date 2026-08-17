import os
import json
from datasets import load_dataset

def download_and_prep_dataset(output_dir="data"):
    print("Downloading MSMARCO-XI dataset...")
    # Loading the validation split or train split. We'll use validation since it's typically smaller and contains good query-passage pairs.
    # MSMARCO-XI has multiple languages. We focus on Hindi ("hi") or we can download all. We'll use english/hindi or default split.
    # Actually MSMARCO-XI has lang='hi' etc.
    # Let's load the english or hindi queries if available, or just the main corpus.
    try:
        # Load passages
        print("Loading corpus...")
        corpus = load_dataset("ai4bharat/MSMARCO-XI", "corpus", split="train")
        
        os.makedirs(output_dir, exist_ok=True)
        corpus_file = os.path.join(output_dir, "corpus.json")
        
        print(f"Loaded {len(corpus)} passages. Saving to {corpus_file}...")
        
        # Save corpus to JSONL for easier processing
        with open(corpus_file, "w", encoding="utf-8") as f:
            for item in corpus:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        print("Dataset preparation complete.")
        
    except Exception as e:
        print(f"Error downloading dataset: {e}")

if __name__ == "__main__":
    download_and_prep_dataset()
