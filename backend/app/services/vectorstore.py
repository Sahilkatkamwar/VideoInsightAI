import chromadb
from chromadb.config import Settings

CHUNK_SIZE = 600   # characters per chunk
OVERLAP = 120       # overlap between chunks for context continuity

# Persistent ChromaDB — survives server restarts
_client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection(
    name="video_chunks",
    metadata={"hnsw:space": "cosine"},
)


# ─── Chunking ────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """Split transcript into overlapping character-level chunks."""
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i : i + CHUNK_SIZE]
        if chunk.strip():
            chunks.append(chunk)
        i += CHUNK_SIZE - OVERLAP
    return chunks


def chunk_timed(timed_segments: list[dict]) -> list[dict]:
    """
    Build chunks from timed transcript segments (YouTube).
    Each chunk carries start_time so we can answer 'first 5 seconds' queries.
    """
    if not timed_segments:
        return []

    chunks = []
    current_text = ""
    current_start = timed_segments[0]["start"]
    current_idx = 0

    for seg in timed_segments:
        current_text += " " + seg["text"]
        if len(current_text) >= CHUNK_SIZE:
            chunks.append(
                {
                    "text": current_text.strip(),
                    "start_time": current_start,
                    "chunk_index": current_idx,
                }
            )
            # overlap: keep last OVERLAP chars
            current_text = current_text[-OVERLAP:]
            current_start = seg["start"]
            current_idx += 1

    # Remaining
    if current_text.strip():
        chunks.append(
            {
                "text": current_text.strip(),
                "start_time": current_start,
                "chunk_index": current_idx,
            }
        )
    return chunks


# ─── Ingest ──────────────────────────────────────────────────────────────────

def ingest_video(
    video_id: str,
    transcript: str,
    timed_segments: list[dict],
    metadata: dict,
    embedder,
) -> int:
    """Chunk + embed + upsert into ChromaDB. Returns number of chunks stored."""

    # Delete existing chunks for this video_id (allows re-ingestion)
    existing = _collection.get(where={"video_id": video_id})
    if existing["ids"]:
        _collection.delete(ids=existing["ids"])

    # Build chunks — prefer timed chunks if available (YouTube)
    if timed_segments:
        raw_chunks = chunk_timed(timed_segments)
        texts = [c["text"] for c in raw_chunks]
        metas = [
            {
                "video_id": video_id,
                "chunk_index": c["chunk_index"],
                "start_time": c["start_time"],
                "creator": str(metadata.get("creator", "")),
                "title": str(metadata.get("title", "")),
                "platform": str(metadata.get("platform", "")),
                "engagement_rate": str(metadata.get("engagement_rate", 0)),
                "views": str(metadata.get("views", 0)),
                "likes": str(metadata.get("likes", 0)),
                "comments": str(metadata.get("comments", 0)),
                "follower_count": str(metadata.get("follower_count", 0)),
            }
            for c in raw_chunks
        ]
    else:
        texts = chunk_text(transcript)
        metas = [
            {
                "video_id": video_id,
                "chunk_index": i,
                "start_time": -1.0,  # unknown
                "creator": str(metadata.get("creator", "")),
                "title": str(metadata.get("title", "")),
                "platform": str(metadata.get("platform", "")),
                "engagement_rate": str(metadata.get("engagement_rate", 0)),
                "views": str(metadata.get("views", 0)),
                "likes": str(metadata.get("likes", 0)),
                "comments": str(metadata.get("comments", 0)),
                "follower_count": str(metadata.get("follower_count", 0)),
            }
            for i in range(len(texts))
        ]

    if not texts:
        return 0

    embeddings = embedder(texts)
    ids = [f"{video_id}_chunk_{i}" for i in range(len(texts))]

    _collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metas,
    )
    return len(texts)


# ─── Retrieve ─────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    video_ids: list[str],
    embedder,
    n_results: int = 8,
) -> list[dict]:
    """Semantic search filtered to given video_ids. Returns ranked chunks."""
    q_vec = embedder([query])[0]

    results = _collection.query(
        query_embeddings=[q_vec],
        n_results=n_results,
        where={"video_id": {"$in": video_ids}},
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "metadata": meta,
                "score": round(1 - dist, 4),  # cosine similarity (higher = better)
            }
        )
    return chunks


def clear_video(video_id: str) -> None:
    """Remove all chunks for a specific video."""
    existing = _collection.get(where={"video_id": video_id})
    if existing["ids"]:
        _collection.delete(ids=existing["ids"])
