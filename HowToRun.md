# How to Run VoiceInGoa

This guide walks you through setting up and running the VoiceInGoa RAG pipeline end-to-end.

## Prerequisites
- Python 3.10+
- Node.js v18+
- InceptionAPI Key (for LLM)
- Sarvam AI Key (for STT)

## 1. Environment Setup
1. Copy `.env.example` to `.env` in the root folder.
2. Fill in your `INCEPTION_API_KEY` and `SARVAM_API_KEY`.

## 2. Backend Setup
1. Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download and Index the Dataset:
   ```bash
   # Downloads the MS MARCO-XI slice and indexes it into local Qdrant
   python data_prep.py
   python retrieval.py
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

## 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 4. Run Benchmarks
To measure P50/P70/P100 latency targets:
```bash
cd backend
venv\Scripts\activate
python benchmarks.py
```

## 5. Deployment (Microsoft Azure)
The backend is Dockerized and ready for **Azure App Service (Web App for Containers)**.
1. Install the Azure CLI and login: `az login`.
2. Create an App Service Plan (ensure you select at least a **B2** tier to accommodate the 1.5GB RAM requirement for PyTorch & Qdrant).
3. Push the `backend` folder directly to Azure App Service via the Azure Portal or using the `az webapp up` command.
4. Ensure you add `INCEPTION_API_KEY` and `SARVAM_API_KEY` to the App Service Environment Variables.
5. In your frontend, update Vercel with the Azure App Service URL.

## 6. Usage
1. Open the live frontend.
2. Complete the onboarding tour.
3. Click the Microphone icon, speak your question clearly, and click again to stop.
4. The system will transcribe, retrieve, and generate the answer in under 200ms!
