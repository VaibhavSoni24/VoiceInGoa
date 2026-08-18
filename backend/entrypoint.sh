#!/bin/bash
set -e

echo "Starting VoiceInGoa Backend Setup..."

# Check if Qdrant database exists
if [ ! -d "qdrant_storage" ]; then
    echo "Qdrant storage not found. Initializing dataset and indexing..."
    
    # Generate golden records
    python golden_records.py
    
    # Download and format dataset (will process full ~100k passages)
    python data_prep.py
    
    # Embed and index dataset into Qdrant
    python retrieval.py
    
    echo "Indexing complete."
else
    echo "Qdrant storage found. Skipping indexing."
fi

echo "Starting FastAPI server..."
# Start the Uvicorn server on port 8000
exec uvicorn main:app --host 0.0.0.0 --port 8000
