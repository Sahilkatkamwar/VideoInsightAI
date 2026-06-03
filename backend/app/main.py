import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ingest, chat, metadata
from app.services.embedder import get_model
from app.routers.media import router as media_router


load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise EnvironmentError("GOOGLE_API_KEY not set in .env")

app = FastAPI(
    title="RAG Video Chatbot API",
    version="1.0.0",
    description="Compare two social media videos using RAG + LangGraph + Gemini",
)

# CORS — allow Next.js dev server and production domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_URL", ""),  # set this in prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(media_router)
app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(metadata.router, tags=["Metadata"])


@app.on_event("startup")
async def startup_event():
    """Pre-load the embedding model so the first request isn't slow."""
    print("[Startup] Pre-loading BGE-M3 embedding model...")
    get_model()
    print("[Startup] Ready.")


@app.get("/")
async def root():
    return {"message": "RAG Video Chatbot API is running."}
