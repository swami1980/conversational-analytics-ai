import json
import uuid
import asyncio
from queue import Queue, Empty
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.middleware import get_current_user
from app.agents.orchestrator import run_agent, StreamEvent
from app.agents.summarizer import format_response, suggest_follow_ups
from app.memory import upsert_session, append_message, get_history, list_sessions, delete_session
from app.config import get_settings

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
_settings = get_settings()


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


def _sse_event(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


async def _stream_agent(
    message: str,
    history: list[dict],
    user: dict,
    session_id: str,
) -> AsyncGenerator[str, None]:
    event_queue: Queue = Queue()

    # Run the blocking Strands agent in a thread pool
    loop = asyncio.get_event_loop()
    agent_future = loop.run_in_executor(
        None,
        run_agent,
        message,
        history,
        event_queue,
        user.get("role", "recruiter"),
    )

    tool_calls_log = []

    yield _sse_event("session", {"session_id": session_id})
    yield _sse_event("status", {"message": "Agent reasoning started..."})

    # Drain the event queue while the agent is running
    while True:
        try:
            item = event_queue.get_nowait()
        except Empty:
            if agent_future.done():
                # Drain any remaining events
                while True:
                    try:
                        item = event_queue.get_nowait()
                    except Empty:
                        break
                    if item is None:
                        break
                    yield _sse_event(item.event_type, item.payload)
                    if item.event_type == "tool_call":
                        tool_calls_log.append(item.payload)
                break
            await asyncio.sleep(0.05)
            continue

        if item is None:
            break

        yield _sse_event(item.event_type, item.payload)
        if item.event_type == "tool_call":
            tool_calls_log.append(item.payload)

    # Get the raw agent answer
    raw_answer = agent_future.result() if agent_future.done() else "No response."

    # Sonnet formatting pass
    yield _sse_event("status", {"message": "Formatting response..."})
    try:
        formatted = format_response(raw_answer, message)
    except Exception:
        formatted = raw_answer

    yield _sse_event("final_answer", {"content": formatted, "raw": raw_answer})

    # Persist to SQLite
    await loop.run_in_executor(
        None, append_message, _settings.sqlite_db_path, session_id, "user", message
    )
    await loop.run_in_executor(
        None, append_message, _settings.sqlite_db_path, session_id, "assistant", formatted, tool_calls_log
    )

    # Haiku follow-up suggestions from last 3 pairs
    updated_history = await loop.run_in_executor(
        None, get_history, _settings.sqlite_db_path, session_id
    )
    qa_pairs = []
    msgs = updated_history
    for i in range(0, len(msgs) - 1, 2):
        if msgs[i]["role"] == "user" and msgs[i + 1]["role"] == "assistant":
            qa_pairs.append({"question": msgs[i]["content"], "answer": msgs[i + 1]["content"]})

    try:
        follow_ups = await loop.run_in_executor(None, suggest_follow_ups, qa_pairs)
    except Exception:
        follow_ups = []

    yield _sse_event("follow_up_questions", {"questions": follow_ups})
    yield _sse_event("done", {})


@router.post("/stream")
async def chat_stream(req: ChatRequest, user: dict = Depends(get_current_user)):
    session_id = req.session_id or str(uuid.uuid4())

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        upsert_session,
        _settings.sqlite_db_path,
        session_id,
        user["sub"],
        user.get("role", "recruiter"),
    )

    history = await loop.run_in_executor(
        None, get_history, _settings.sqlite_db_path, session_id
    )

    return StreamingResponse(
        _stream_agent(req.message, history, user, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
async def get_sessions(user: dict = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    sessions = await loop.run_in_executor(
        None, list_sessions, _settings.sqlite_db_path, user["sub"]
    )
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, user: dict = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    history = await loop.run_in_executor(
        None, get_history, _settings.sqlite_db_path, session_id
    )
    return {"session_id": session_id, "messages": history}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, user: dict = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, delete_session, _settings.sqlite_db_path, session_id
    )
    return {"deleted": session_id}
