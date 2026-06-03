import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..models.schemas import ChatRequest
from ..agent.graph import agent_graph
from ..agent.nodes import llm, build_streaming_messages
from ..services.vectorstore import retrieve
from ..services.embedder import embed

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    SSE streaming endpoint.
    Flow:
      1. Run retrieval node synchronously (fast, local ChromaDB)
      2. Build full prompt with metadata + chunks
      3. Stream Gemini
      4. Persist turn to LangGraph memory
    """

    async def event_stream():
        try:
            # Step 1: Retrieve relevant chunks (blocking but fast ~10ms)
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None, retrieve, req.message, ["A", "B"], embed, 8
            )

            # Step 2: Build messages with context
            state = {
                "query": req.message,
                "metadata_a": req.metadata_a,
                "metadata_b": req.metadata_b,
                "context_chunks": chunks,
                "messages": [],  # LangGraph loads history from checkpointer
            }

            # Load conversation history from LangGraph memory
            config = {"configurable": {"thread_id": req.session_id}}
            snapshot = agent_graph.get_state(config)
            if snapshot and snapshot.values:
                state["messages"] = snapshot.values.get("messages", [])

            messages = build_streaming_messages(state)

            # Step 3: Stream tokens from Gemini
            full_response = ""
            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    full_response += token
                    payload = json.dumps({"type": "token", "content": token})
                    yield f"data: {payload}\n\n"

            # Step 4: Send citation sources
            sources = [
                {
                    "video_id": c["metadata"]["video_id"],
                    "chunk_index": c["metadata"]["chunk_index"],
                    "start_time": c["metadata"].get("start_time", -1),
                    "text_preview": c["text"][:120],
                    "score": c["score"],
                }
                for c in chunks[:5]
            ]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

            # Step 5: Persist turn to LangGraph memory
            user_msg = {"role": "user", "content": req.message}
            assistant_msg = {"role": "assistant", "content": full_response}
            await loop.run_in_executor(
                None,
                _persist_turn,
                state,
                user_msg,
                assistant_msg,
                config,
            )

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_payload = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )


def _persist_turn(state: dict, user_msg: dict, assistant_msg: dict, config: dict):
    """Save the completed turn into LangGraph's MemorySaver."""
    new_state = {**state, "messages": [user_msg, assistant_msg]}
    agent_graph.update_state(config, new_state)


@router.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation memory for a session."""
    return {"message": f"Session {session_id} cleared (restart server to fully reset MemorySaver)."}
