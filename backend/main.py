import os
import time
import tempfile
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables early (MUST be before importing pipeline)
from dotenv import load_dotenv
load_dotenv()

from pipeline import call_stt, run_rag_pipeline

app = FastAPI(title="VoiceInGoa API", description="Sub-200ms Voice-enabled RAG Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "VoiceInGoa API is running."}

@app.post("/api/ask-voice")
async def ask_voice(file: UploadFile = File(...)):
    # 1. Save uploaded audio temporarily
    start_time = time.time()
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        content = await file.read()
        temp_audio.write(content)
        temp_audio.close()
        
        # 2. Transcribe
        stt_start = time.time()
        try:
            transcript = call_stt(temp_audio.name)
        except Exception as e:
            return {"status": "error", "message": f"STT failed: {str(e)}"}
        stt_ms = int((time.time() - stt_start) * 1000)
        
        # If transcript is empty
        if not transcript.strip():
            return {"status": "error", "message": "Could not understand audio."}
            
        # 3. RAG Pipeline
        rag_result = run_rag_pipeline(transcript)
        
        # 4. Construct Response
        response = {
            "status": "success",
            "transcript": transcript,
            "answer": {
                "refused": rag_result["refused"],
                "content": rag_result["content"],
                "reason": rag_result.get("reason"),
                "citations": rag_result.get("citations", [])
            },
            "metrics": rag_result["metrics"]
        }
        response["metrics"]["stt_ms"] = stt_ms
        
        return response
        
    finally:
        # Cleanup
        if os.path.exists(temp_audio.name):
            os.remove(temp_audio.name)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
