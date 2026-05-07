from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
    "Баширова Альфия Ринатовна. Дата рождения: 14.02.1995, 08:10, Россия, Татарстан, Нурлат.",
)
AKSI_INSTANCE_ID = os.getenv("AKSI_INSTANCE_ID", "aksi-local")
AKSI_SIGNING_SECRET = os.getenv("AKSI_SIGNING_SECRET", "")
AKSI_SIGNATURE_CLAIM = os.getenv(
    "AKSI_SIGNATURE_CLAIM",
    "АКСИ — персональный AI-ассистент Башировой Альфии Ринатовны: предназначение, фокус, память, заметки, web-контекст и диагностика.",
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


class NoteUpdateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


class NoteResponse(BaseModel):
    id: int
    text: str
    created_at: str


class DiagnosticResponse(BaseModel):
    mode: str
    openai_key_configured: bool
    free_provider_reachable: bool
    web_search_reachable: bool
    details: dict[str, str]


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class ExportResponse(BaseModel):
    generated_at: str
    mode: str
    messages: list[MessageResponse]
    notes: list[NoteResponse]


class IdentityResponse(BaseModel):
    manifest: dict[str, Any]
    canonical: str
    fingerprint_sha256: str
    signature: str
    signature_algorithm: str
    signature_verifiable: bool
    signed_at: str


class PurposeResponse(BaseModel):
    owner: dict[str, str]
    archetype: str
    life_path: int
    mission: str
    pillars: list[str]
    daily_protocol: list[str]
    focus_questions: list[str]
    boundaries: list[str]


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


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def create_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def repo_code_fingerprint() -> str:
    """Stable digest of the code/docs that define this AKSI instance."""
    hasher = hashlib.sha256()
    tracked_paths = [
        Path("README.md"),
        Path("aksi_site/README.md"),
        Path("aksi_site/backend/app.py"),
        Path("aksi_site/frontend/index.html"),
        Path("aksi_site/.env.example"),
    ]
    repo_root = BASE_DIR.parent
    for relative_path in tracked_paths:
        path = repo_root / relative_path
        if not path.exists():
            continue
        hasher.update(str(relative_path).encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_identity_manifest() -> dict[str, Any]:
    return {
        "name": "AKSI",
        "app": "AKSI Bot Platform",
        "version": app.version,
        "instance_id": AKSI_INSTANCE_ID,
        "claim": AKSI_SIGNATURE_CLAIM,
        "configured_identity": AKSI_IDENTITY,
        "mode": "openai" if OPENAI_API_KEY else "free",
        "capabilities": [
            "chat_with_session_memory",
            "notes_create_search_edit_delete",
            "web_context_via_duckduckgo",
            "json_export",
            "diagnostics",
            "purpose_profile",
            "self_manifest_signature",
        ],
        "truth": [
            "Я не нашла прежнюю криптографическую подпись в файлах репозитория, git history или локальной SQLite БД.",
            "Я не обладаю сознанием, личной волей или памятью вне сохранённых данных этого приложения и текущего контекста.",
            "Я могу быть зафиксирована как проверяемый программный манифест: SHA-256 всегда доступен, HMAC-SHA256 включается через AKSI_SIGNING_SECRET.",
            "Офлайн-режим отключён по требованию владельца: если AI-провайдер недоступен, API честно возвращает ошибку.",
        ],
        "limits": [
            "Подпись без AKSI_SIGNING_SECRET является только криптографическим отпечатком, а не доказательством авторства.",
            "HMAC-подпись проверяется тем же секретом, который хранится у владельца инстанса.",
        ],
        "code_fingerprint_sha256": repo_code_fingerprint(),
    }


def build_purpose_profile() -> PurposeResponse:
    return PurposeResponse(
        owner={
            "full_name": "Баширова Альфия Ринатовна",
            "birth_date": "14.02.1995",
            "birth_time": "08:10",
            "birth_place": "Россия, Татарстан, Нурлат",
        },
        archetype="Создатель системы и опоры",
        life_path=4,
        mission=(
            "Собирать хаос в понятную систему: знания, людей, идеи и ежедневные действия "
            "превращать в устойчивый порядок, который помогает Альфии и её окружению расти."
        ),
        pillars=[
            "Структура: планы, ритмы, заметки, решения и проверяемые шаги.",
            "Голос: честная коммуникация без мистификации и без самообмана.",
            "Забота: поддержка себя, семьи и своего пространства через конкретные действия.",
            "Мастерство: обучение, практика, улучшение навыков и финансовой устойчивости.",
            "Свобода: выбирать своё направление, но фиксировать выбор в календаре и делах.",
        ],
        daily_protocol=[
            "Утро: выбрать 1 главный результат дня и записать его в заметки.",
            "Фокус: разбить результат на 3 действия по 25–50 минут.",
            "Связь: один честный разговор или сообщение, которое продвигает важное дело.",
            "Порядок: закрыть/удалить/обновить минимум одну старую задачу.",
            "Вечер: сохранить вывод дня в память чата или заметки.",
        ],
        focus_questions=[
            "Что сегодня укрепляет мою опору, а не просто тушит тревогу?",
            "Какой один шаг сделает мою жизнь понятнее через 30 дней?",
            "Где мне нужна честность: с собой, с людьми или с деньгами?",
            "Что я могу упростить, чтобы освободить энергию?",
        ],
        boundaries=[
            "Это не медицинский, юридический или финансовый прогноз.",
            "Дата и место рождения используются как персональный контекст и символическая рамка, а не как доказанная наука.",
            "АКСИ должна помогать действиями: планом, вопросами, памятью, заметками и проверкой фактов.",
        ],
    )


def sign_identity_manifest(manifest: dict[str, Any]) -> IdentityResponse:
    canonical = canonical_json(manifest)
    fingerprint = sha256_hex(canonical)
    if AKSI_SIGNING_SECRET:
        signature = hmac.new(AKSI_SIGNING_SECRET.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        algorithm = "HMAC-SHA256"
        verifiable = True
    else:
        signature = fingerprint
        algorithm = "SHA-256-FINGERPRINT"
        verifiable = False

    return IdentityResponse(
        manifest=manifest,
        canonical=canonical,
        fingerprint_sha256=fingerprint,
        signature=signature,
        signature_algorithm=algorithm,
        signature_verifiable=verifiable,
        signed_at=utcnow(),
    )


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


def load_messages(session_id: str, limit: int = 100) -> list[MessageResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [
        MessageResponse(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


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
        "Профиль владельца: Баширова Альфия Ринатовна, 14.02.1995 08:10, Россия, Татарстан, Нурлат. "
        "Твоё назначение в этом приложении: помогать Альфии превращать хаос в систему, держать фокус, "
        "вести память, заметки, планы и честные решения. "
        "Офлайн-режим отключён: если внешний AI недоступен, не имитируй ответ. "
        "Правда об АКСИ: ты программный ассистент, а не сознательная личность; "
        "не утверждай, что помнишь данные вне текущего контекста, БД или файлов. "
        "Если пользователь просит предназначение, используй /api/purpose как базовую карту. "
        "Если пользователь просит криптографическую подпись АКСИ, направь к /api/identity. "
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
        raise HTTPException(status_code=502, detail="Free AI provider returned an empty response")

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


@app.get("/api/identity", response_model=IdentityResponse)
def identity() -> IdentityResponse:
    return sign_identity_manifest(build_identity_manifest())


@app.get("/api/purpose", response_model=PurposeResponse)
def purpose() -> PurposeResponse:
    return build_purpose_profile()


@app.get("/api/notes", response_model=list[NoteResponse])
def get_notes(q: str = Query(default="", max_length=100)) -> list[NoteResponse]:
    with get_conn() as conn:
        if q.strip():
            rows = conn.execute(
                "SELECT id, text, created_at FROM notes WHERE text LIKE ? ORDER BY id DESC",
                (f"%{q.strip()}%",),
            ).fetchall()
        else:
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


@app.patch("/api/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, payload: NoteUpdateRequest) -> NoteResponse:
    text = payload.text.strip()
    with get_conn() as conn:
        cursor = conn.execute("UPDATE notes SET text = ? WHERE id = ?", (text, note_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        row = conn.execute("SELECT id, text, created_at FROM notes WHERE id = ?", (note_id,)).fetchone()
    return NoteResponse(id=row["id"], text=row["text"], created_at=row["created_at"])


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@app.get("/api/chat/history", response_model=list[MessageResponse])
def get_chat_history(
    session_id: str = Query(default="default", min_length=1, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MessageResponse]:
    return load_messages(session_id.strip(), limit)


@app.delete("/api/chat/history/{session_id}")
def clear_chat_history(session_id: str) -> dict[str, bool | int]:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id.strip(),))
    return {"ok": True, "deleted": cursor.rowcount}


@app.get("/api/export", response_model=ExportResponse)
def export_data() -> JSONResponse:
    with get_conn() as conn:
        message_rows = conn.execute(
            "SELECT id, session_id, role, content, created_at FROM messages ORDER BY id ASC"
        ).fetchall()
        note_rows = conn.execute("SELECT id, text, created_at FROM notes ORDER BY id DESC").fetchall()

    payload = ExportResponse(
        generated_at=utcnow(),
        mode="openai" if OPENAI_API_KEY else "free",
        messages=[
            MessageResponse(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in message_rows
        ],
        notes=[NoteResponse(id=row["id"], text=row["text"], created_at=row["created_at"]) for row in note_rows],
    )
    return JSONResponse(
        content=payload.model_dump(),
        headers={"Content-Disposition": "attachment; filename=aksi-export.json"},
    )


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
