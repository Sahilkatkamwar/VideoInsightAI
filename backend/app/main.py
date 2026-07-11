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


def _csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


allowed_origins = sorted(
    {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://video-insight-ai-olive.vercel.app",
        *_csv_env("FRONTEND_URL"),
        *_csv_env("FRONTEND_URLS"),
    }
)

app = FastAPI(
    title="RAG Video Chatbot API",
    version="1.0.0",
    description="Compare two social media videos using RAG + LangGraph + Gemini",
)

# CORS - allow local development plus Vercel production/preview deployments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
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
    print("[Startup] Initializing Gemini embeddings...")
    get_model()
    print("[Startup] Ready.")

@app.get("/")
async def root():
    return {"message": "RAG Video Chatbot API is running."}
