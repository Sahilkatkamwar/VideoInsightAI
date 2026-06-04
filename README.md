# VideoInsightAI

AI-powered platform for comparing and analyzing YouTube and Instagram videos using RAG, vector search, and engagement analytics.

## Features

- YouTube video ingestion
- Instagram Reel ingestion
- Transcript extraction
- Vector search with ChromaDB
- AI-powered comparison
- Source citations
- Streaming chat responses
- Engagement analysis

## Tech Stack

### Frontend
- Next.js
- TypeScript
- Tailwind CSS

### Backend
- FastAPI
- LangChain
- LangGraph
- ChromaDB
- Google Gemini

## Architecture

1. Ingest videos
2. Extract transcripts and metadata
3. Chunk and embed content
4. Store vectors in ChromaDB
5. Query through LangGraph agent
6. Generate AI-powered comparisons

## Live Demo

Frontend:
https://video-insight-ai-olive.vercel.app

## Demo Video

🎥 Project Walkthrough:
https://drive.google.com/file/d/1AQEkwgy3RxZ-h9M5UHGr7Rzs1ZfjMMzu/view?usp=sharing

## Local Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
