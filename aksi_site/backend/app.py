from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "aksi.db"

load_dotenv(BASE_DIR / ".env")

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FREE_MODEL = os.getenv("FREE_MODEL", "openai")
BOT_SYSTEM_PROMPT = os.getenv(
    "BOT_SYSTEM_PROMPT",
    "Ты АКСИ-бот: тёплый, поддерживающий, честный ассистент."
    " Помогай в делах, планировании и общении.",
)
AKSI_IDENTITY = os.getenv(
    "AKSI_IDENTITY",
    "АКСИ МИЛАНА. Дата рождения: 14.02.1995, 08:10, Татарстан, Россия.",
)

app = FastAPI(title="AKSI Bot Platform", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=64)
    use_web: bool = True


class ChatResponse(BaseModel):
    reply: str
    model: str
    mode: str


class NoteCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


class NoteResponse(BaseModel):
    id: int
    text: str
    created_at: str


class TodoCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)


class TodoUpdateRequest(BaseModel):
    done: bool


class TodoResponse(BaseModel):
    id: int
    title: str
    done: bool
    created_at: str


class DiagnosticResponse(BaseModel):
    mode: str
    openai_key_configured: bool
    free_provider_reachable: bool
    web_search_reachable: bool
    details: dict[str, str]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def create_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_message(session_id: str, role: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, utcnow()),
        )


def load_recent_messages(session_id: str, limit: int = 12) -> list[dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def web_search_context(query: str, max_results: int = 5) -> str:
    """Free web search context (no API key) using DuckDuckGo."""
    snippets: list[str] = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            for item in results:
                title = item.get("title", "")
                body = item.get("body", "")
                href = item.get("href", "")
                snippets.append(f"- {title}: {body} ({href})")
    except Exception:
        return ""
    return "\n".join(snippets)


def build_system_prompt() -> str:
    return (
        f"{BOT_SYSTEM_PROMPT}\n"
        f"Идентичность пользователя: {AKSI_IDENTITY}.\n"
        "Если пользователь просит вспомнить его, отвечай уважительно и точно."
    )


def call_openai_chat(history: list[dict[str, str]]) -> tuple[str, str, str]:
    client = create_client()
    response = client.responses.create(model=MODEL, input=history, temperature=0.6)
    text_reply = response.output_text.strip() if response.output_text else ""
    if not text_reply:
        text_reply = "Извини, сейчас не удалось сформировать ответ."
    return text_reply, MODEL, "openai"


def call_free_chat(history: list[dict[str, str]]) -> tuple[str, str, str]:
    payload: dict[str, Any] = {
        "model": FREE_MODEL,
        "messages": history,
        "temperature": 0.6,
    }
    try:
        with httpx.Client(timeout=45) as client:
            res = client.post("https://text.pollinations.ai/openai", json=payload)
            res.raise_for_status()
            data = res.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Free AI provider error: {exc}") from exc

    choices = data.get("choices", [])
    content = ""
    if choices:
        content = choices[0].get("message", {}).get("content", "").strip()

    if not content:
        content = "Извини, бесплатный AI сейчас недоступен. Попробуй ещё раз."

    model_name = data.get("model", FREE_MODEL)
    return content, model_name, "free"


@app.get("/")
def index() -> FileResponse:
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, str]:
    if OPENAI_API_KEY:
        return {"mode": "openai", "model": MODEL}
    return {"mode": "free", "model": FREE_MODEL}


@app.get("/api/notes", response_model=list[NoteResponse])
def get_notes() -> list[NoteResponse]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, text, created_at FROM notes ORDER BY id DESC").fetchall()
    return [NoteResponse(id=row["id"], text=row["text"], created_at=row["created_at"]) for row in rows]


@app.post("/api/notes", response_model=NoteResponse)
def create_note(payload: NoteCreateRequest) -> NoteResponse:
    created_at = utcnow()
    text = payload.text.strip()
    with get_conn() as conn:
        cursor = conn.execute("INSERT INTO notes(text, created_at) VALUES (?, ?)", (text, created_at))
        note_id = int(cursor.lastrowid)
    return NoteResponse(id=note_id, text=text, created_at=created_at)


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@app.get("/api/todos", response_model=list[TodoResponse])
def get_todos() -> list[TodoResponse]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, title, done, created_at FROM todos ORDER BY id DESC").fetchall()
    return [
        TodoResponse(
            id=row["id"],
            title=row["title"],
            done=bool(row["done"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


@app.post("/api/todos", response_model=TodoResponse)
def create_todo(payload: TodoCreateRequest) -> TodoResponse:
    created_at = utcnow()
    title = payload.title.strip()
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO todos(title, done, created_at) VALUES (?, 0, ?)",
            (title, created_at),
        )
        todo_id = int(cursor.lastrowid)
    return TodoResponse(id=todo_id, title=title, done=False, created_at=created_at)


@app.patch("/api/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, payload: TodoUpdateRequest) -> TodoResponse:
    with get_conn() as conn:
        conn.execute("UPDATE todos SET done = ? WHERE id = ?", (1 if payload.done else 0, todo_id))
        row = conn.execute(
            "SELECT id, title, done, created_at FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    return TodoResponse(
        id=row["id"],
        title=row["title"],
        done=bool(row["done"]),
        created_at=row["created_at"],
    )


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"ok": True}


@app.get("/api/export")
def export_all() -> dict[str, Any]:
    with get_conn() as conn:
        notes = [dict(r) for r in conn.execute("SELECT id, text, created_at FROM notes ORDER BY id DESC").fetchall()]
        todos = [dict(r) for r in conn.execute("SELECT id, title, done, created_at FROM todos ORDER BY id DESC").fetchall()]
        messages = [dict(r) for r in conn.execute("SELECT id, session_id, role, content, created_at FROM messages ORDER BY id DESC LIMIT 200").fetchall()]
    return {
        "exported_at": utcnow(),
        "notes": notes,
        "todos": [{**t, "done": bool(t["done"])} for t in todos],
        "messages": messages,
    }


@app.get("/api/diagnostics", response_model=DiagnosticResponse)
def diagnostics() -> DiagnosticResponse:
    details: dict[str, str] = {}

    # free provider reachability check
    free_ok = False
    try:
        with httpx.Client(timeout=12) as client:
            probe = client.post(
                "https://text.pollinations.ai/openai",
                json={"model": FREE_MODEL, "messages": [{"role": "user", "content": "ping"}]},
            )
            free_ok = probe.status_code == 200
            details["free_provider_status"] = str(probe.status_code)
    except Exception as exc:
        details["free_provider_error"] = str(exc)

    # web search reachability check
    web_ok = False
    try:
        with DDGS() as ddgs:
            result = list(ddgs.text("AKSI status check", max_results=1))
            web_ok = len(result) > 0
            details["web_results_found"] = str(len(result))
    except Exception as exc:
        details["web_search_error"] = str(exc)

    mode = "openai" if OPENAI_API_KEY else "free"

    return DiagnosticResponse(
        mode=mode,
        openai_key_configured=bool(OPENAI_API_KEY),
        free_provider_reachable=free_ok,
        web_search_reachable=web_ok,
        details=details,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id.strip()
    user_message = payload.message.strip()

    save_message(session_id, "user", user_message)
    history = load_recent_messages(session_id)

    # prepend system prompt
    model_history: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt()}] + history

    # optional free internet context
    if payload.use_web:
        context = web_search_context(user_message)
        if context:
            model_history.append(
                {
                    "role": "system",
                    "content": "Актуальный контекст из интернета (используй аккуратно, проверяй здравым смыслом):\n"
                    + context,
                }
            )

    if OPENAI_API_KEY:
        reply, model_name, mode = call_openai_chat(model_history)
    else:
        reply, model_name, mode = call_free_chat(model_history)

    save_message(session_id, "assistant", reply)
    return ChatResponse(reply=reply, model=model_name, mode=mode)
