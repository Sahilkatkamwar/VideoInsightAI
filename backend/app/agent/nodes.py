import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from ..services.vectorstore import retrieve
from ..services.embedder import embed
from .prompts import SYSTEM_PROMPT

load_dotenv()

print("GOOGLE_API_KEY FOUND:", bool(os.getenv("GOOGLE_API_KEY")))
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)


def retrieve_node(state: dict) -> dict:
    """
    Fetch top-k relevant chunks from ChromaDB for the current query.
    Retrieves from both Video A and B simultaneously.
    """
    query = state["query"]

    # Get chunks from both videos
    chunks = retrieve(query, ["A", "B"], embed, n_results=8)

    # Separate first-5-second chunks for hook-related queries
    hook_keywords = {"hook", "open", "first", "start", "begin", "intro", "seconds"}
    is_hook_query = any(kw in query.lower() for kw in hook_keywords)

    if is_hook_query:
        # Boost early-timestamp chunks
        hook_chunks = [
            c for c in chunks if float(c["metadata"].get("start_time", -1)) < 10.0
        ]
        if hook_chunks:
            # Put hook chunks first, dedup
            hook_ids = {c["text"] for c in hook_chunks}
            rest = [c for c in chunks if c["text"] not in hook_ids]
            chunks = hook_chunks + rest

    return {"context_chunks": chunks}


def generate_node(state: dict) -> dict:
    """
    Build the full prompt with metadata + retrieved chunks,
    call Gemini, return assistant message.
    This node is used for non-streaming (batch) calls.
    For streaming, the router calls llm.astream() directly.
    """
    meta_a = state.get("metadata_a", {})
    meta_b = state.get("metadata_b", {})
    chunks = state.get("context_chunks", [])

    context_str = _build_context(chunks)
    meta_str = _build_meta(meta_a, meta_b)

    messages = _build_messages(state, meta_str, context_str)

    response = llm.invoke(messages)
    new_msg = {"role": "assistant", "content": response.content}

    return {
        "messages": state.get("messages", []) + [new_msg],
        "last_response": response.content,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_context(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        vid = c["metadata"]["video_id"]
        idx = c["metadata"]["chunk_index"]
        st = c["metadata"].get("start_time", -1)
        time_label = f" @{float(st):.1f}s" if float(st) >= 0 else ""
        lines.append(f"[Video {vid}, chunk {idx}{time_label}]\n{c['text']}")
    return "\n\n".join(lines)


def _build_meta(meta_a: dict, meta_b: dict) -> str:
    def fmt(label, m):
        return (
            f"Video {label}: \"{m.get('title', 'N/A')}\"\n"
            f"  Platform: {m.get('platform', 'N/A')}\n"
            f"  Creator: @{m.get('creator', 'N/A')} ({m.get('follower_count', 0):,} followers)\n"
            f"  Views: {m.get('views', 0):,} | Likes: {m.get('likes', 0):,} | Comments: {m.get('comments', 0):,}\n"
            f"  Engagement Rate: {m.get('engagement_rate', 0)}%\n"
            f"  Duration: {m.get('duration', 0)}s | Upload: {m.get('upload_date', 'N/A')}\n"
            f"  Hashtags: {', '.join(m.get('hashtags', [])[:10])}"
        )
    return fmt("A", meta_a) + "\n\n" + fmt("B", meta_b)


def _build_messages(state: dict, meta_str: str, context_str: str) -> list[dict]:
    history = state.get("messages", [])
    user_content = (
        f"## Video Metadata\n{meta_str}\n\n"
        f"## Retrieved Transcript Chunks\n{context_str}\n\n"
        f"## Question\n{state['query']}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_content},
    ]


# Expose helpers for the streaming router
def build_streaming_messages(state: dict) -> list[dict]:
    meta_str = _build_meta(state.get("metadata_a", {}), state.get("metadata_b", {}))
    context_str = _build_context(state.get("context_chunks", []))
    return _build_messages(state, meta_str, context_str)
