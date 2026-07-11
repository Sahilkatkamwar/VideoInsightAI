import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

_embeddings = None

def get_model():
    global _embeddings

    if _embeddings is None:
        print("[Embedder] Initializing Gemini embeddings...")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    return _embeddings


def embed(texts: list[str]) -> list[list[float]]:
    model = get_model()
    return model.embed_documents(texts)
