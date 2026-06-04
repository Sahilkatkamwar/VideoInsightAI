import os
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from ..services.vectorstore import retrieve
from ..services.embedder import embed
from .prompts import SYSTEM_PROMPT

load_dotenv()

class ChatState(TypedDict, total=False):
    query: str
    messages: List[Dict[str, Any]]

    metadata_a: Dict[str, Any]
    metadata_b: Dict[str, Any]

    context_chunks: List[Dict[str, Any]]

    last_response: str
    sources: List[Dict[str, Any]]

print("GOOGLE_API_KEY FOUND:", bool(os.getenv("GOOGLE_API_KEY")))
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
    streaming=True,
)

def format_chunk_sources(chunks: list[dict]) -> list[dict]:
    sources = []

    for c in chunks:
        meta = c["metadata"]

        sources.append({
            "video_id": meta.get("video_id", ""),
            "chunk_index": meta.get("chunk_index", -1),
            "start_time": meta.get("start_time", -1),
            "score": c.get("score", 0),
            "title": meta.get("title", ""),
            "creator": meta.get("creator", ""),
        })

    return sources


def retrieve_node(state: ChatState) -> ChatState:
    """
    Retrieve relevant chunks from both videos.
    Adds hook boosting and source tracking.
    """


    query = state["query"]

    chunks = retrieve(
        query=query,
        video_ids=["A", "B"],
        embedder=embed,
        n_results=4
    )
    
    print("\nRETRIEVED CHUNKS:")
    for c in chunks:
        print(
            c["metadata"].get("video_id"),
            c["metadata"].get("chunk_index"),
            c.get("score")
        )

    hook_keywords = {
        "hook",
        "open",
        "opening",
        "first",
        "start",
        "begin",
        "intro",
        "introduction",
        "seconds"
    }

    is_hook_query = any(
        kw in query.lower()
        for kw in hook_keywords
    )

    if is_hook_query:

        hook_chunks = [
            c
            for c in chunks
            if float(
                c["metadata"].get(
                    "start_time",
                    -1
                )
            ) < 10.0
        ]

        if hook_chunks:

            seen = {
                c["text"]
                for c in hook_chunks
            }

            remaining = [
                c
                for c in chunks
                if c["text"] not in seen
            ]

            chunks = hook_chunks + remaining

    return {
        **state,
        "context_chunks": chunks,
        "sources": format_chunk_sources(chunks)
    }


def generate_node(state: ChatState) -> ChatState:
    """
    Non-streaming generation.
    """
    print("GENERATE NODE CALLED")

    meta_a = state.get("metadata_a", {})
    meta_b = state.get("metadata_b", {})

    chunks = state.get("context_chunks", [])

    context_str = _build_context(chunks)

    meta_str = _build_meta(
        meta_a,
        meta_b
    )

    messages = _build_messages(
        state,
        meta_str,
        context_str
    )

    response = llm.invoke(messages)

    answer = (
        response.content
        if hasattr(response, "content")
        else str(response)
    )

    new_msg = {
        "role": "assistant",
        "content": answer
    }

    return {
        **state,
        "messages": (
            state.get("messages", [])
            + [new_msg]
        ),
        "last_response": answer,
        "answer": answer
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_context(chunks: list[dict]) -> str:

    if not chunks:
        return "No relevant transcript chunks found."

    lines = []

    for c in chunks:

        meta = c["metadata"]

        vid = meta.get(
            "video_id",
            "?"
        )

        idx = meta.get(
            "chunk_index",
            -1
        )

        start_time = float(
            meta.get(
                "start_time",
                -1
            )
        )

        timestamp = (
            f" @{start_time:.1f}s"
            if start_time >= 0
            else ""
        )

        lines.append(
            f"[Video {vid} chunk {idx}{timestamp}]\n"
            f"{c['text']}"
        )

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


def _build_messages(state: ChatState, meta_str: str, context_str: str) -> list[dict]:
    history = state.get("messages", [])
    user_content = f"""
## Instructions

Use ONLY the supplied metadata and transcript chunks.

When making claims, cite evidence using:

[Video A chunk X]
[Video B chunk X]

Examples:

- Video A uses a stronger hook [Video A chunk 0]
- Video B has a clearer CTA [Video B chunk 6]

Never invent citations.

Only cite chunks that appear in the retrieved context.

## Video Metadata
{meta_str}

## Retrieved Transcript Chunks

{context_str}

## User Question

{state['query']}
"""
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
