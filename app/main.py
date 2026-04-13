from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import STATIC_DIR
from .persona_service import PersonaService


app = FastAPI(title="Scaler Persona")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

persona = PersonaService()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict] = Field(default_factory=list)


class BookingRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    start_at: str = Field(min_length=5)
    notes: str = ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/webhook")
def webhook_info() -> dict:
    return {
        "status": "ok",
        "message": "Webhook endpoint is live. POST Twilio form data or JSON here.",
    }


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        incoming_text = str(form.get("Body", "")).strip()
        sender = str(form.get("From", "")).strip()
        if not incoming_text:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response><Message>Webhook received, but no message body was provided.</Message></Response>"
            )
            return Response(content=twiml, media_type="application/xml")

        reply = persona.chat(incoming_text)
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Message>{_escape_xml(reply['answer'])}</Message>"
            "</Response>"
        )
        return Response(
            content=twiml,
            media_type="application/xml",
            headers={"X-Webhook-Sender": sender},
        )

    payload = await request.json()
    incoming_text = _extract_message_from_payload(payload)
    if not incoming_text:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "No user message found in webhook payload.",
                "received_keys": sorted(payload.keys()),
            },
        )

    reply = persona.chat(incoming_text)
    return JSONResponse(
        content={
            "status": "ok",
            "input": incoming_text,
            "answer": reply["answer"],
            "sources": reply["sources"],
        }
    )


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    try:
        return persona.chat(message=payload.message, history=payload.history)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/availability")
def availability() -> dict:
    try:
        return persona.availability()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/calendar/event-types")
def calendar_event_types() -> dict:
    try:
        return persona.calendar.get_event_types()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/book")
def book(payload: BookingRequest) -> dict:
    try:
        return persona.book(
            name=payload.name,
            email=payload.email,
            start_at=payload.start_at,
            notes=payload.notes,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/voice/config")
def voice_config() -> dict:
    return persona.voice_config()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _extract_message_from_payload(payload: dict) -> str:
    candidates = [
        payload.get("message"),
        payload.get("text"),
        payload.get("transcript"),
        payload.get("input"),
    ]

    message = payload.get("message")
    if isinstance(message, dict):
        candidates.extend(
            [
                message.get("content"),
                message.get("text"),
                message.get("transcript"),
            ]
        )

    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if not isinstance(item, dict):
                continue
            if item.get("role") in {"user", "caller"}:
                candidates.extend(
                    [
                        item.get("content"),
                        item.get("text"),
                        item.get("message"),
                    ]
                )
                break

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
