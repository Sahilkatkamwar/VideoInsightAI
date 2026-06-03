from sentence_transformers import SentenceTransformer

# Singleton — loaded once when backend starts, reused for every request
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("[Embedder] Loading BAAI/bge-m3 — first run downloads ~2GB, cached after...")
        _model = SentenceTransformer("BAAI/bge-m3")
        print("[Embedder] Model loaded.")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns list of float vectors."""
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()
