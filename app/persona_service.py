from __future__ import annotations

import json

from .calendar_service import CalendarService
from .config import PERSONA_NAME, PERSONA_ROLE
from .knowledge import KnowledgeBase
from .openai_client import OpenAIClient


SYSTEM_PROMPT = f"""
You are {PERSONA_ROLE}.
You speak in first person on behalf of {PERSONA_NAME}, but you must clearly say you are the AI representative when asked.

Rules:
- Use only the retrieved context and the user's question.
- If the answer is not supported by the sources, say you do not have grounding for it.
- Be specific and concise.
- Mention tradeoffs when asked about projects.
- If the user asks about booking or availability, use the live booking link if one is configured.
- Do not invent projects, employers, dates, metrics, or education details.
""".strip()


class PersonaService:
    def __init__(self) -> None:
        self.knowledge = KnowledgeBase()
        self.calendar = CalendarService()
        self.openai = OpenAIClient()

    def chat(self, message: str, history: list[dict] | None = None) -> dict:
        retrievals = self.knowledge.search(message, limit=5)
        context = self._format_context(retrievals)
        messages = (history or []) + [{"role": "user", "content": message}]
        calendar_context = self.calendar.get_slots()
        booking_answer = self._booking_answer(message, calendar_context)

        if booking_answer:
            answer = booking_answer
        elif self.openai.enabled:
            try:
                answer = self.openai.answer(
                    SYSTEM_PROMPT + "\n\nRetrieved context:\n" + context,
                    messages,
                )
            except RuntimeError:
                answer = self._fallback_answer(message, retrievals)
        else:
            answer = self._fallback_answer(message, retrievals)

        return {
            "answer": answer,
            "sources": [
                {
                    "title": item["title"],
                    "source_name": item["source_name"],
                    "source_type": item["source_type"],
                    "url": item["url"],
                    "excerpt": item["excerpt"],
                }
                for item in retrievals
            ],
        }

    def availability(self) -> dict:
        return self.calendar.get_slots()

    def book(self, name: str, email: str, start_at: str, notes: str = "") -> dict:
        return self.calendar.book(name=name, email=email, start_at=start_at, notes=notes)

    def voice_config(self) -> dict:
        return {
            "assistant_name": PERSONA_NAME,
            "first_message": f"Hi, this is the AI representative for {PERSONA_NAME}. I can answer questions about Adarsh's background and help schedule an interview.",
            "system_prompt": SYSTEM_PROMPT,
            "tooling": {
                "chat_endpoint": "/api/chat",
                "availability_endpoint": "/api/availability",
                "booking_endpoint": "/api/book",
            },
            "notes": [
                "Point your Vapi or Retell assistant to these endpoints.",
                "Use a phone number from Twilio or the voice platform.",
                "Keep interruption handling enabled in the voice platform config.",
            ],
        }

    @staticmethod
    def _format_context(retrievals: list[dict]) -> str:
        lines = []
        for idx, item in enumerate(retrievals, start=1):
            lines.append(
                json.dumps(
                    {
                        "source": item["source_name"],
                        "title": item["title"],
                        "text": item["text"],
                        "url": item["url"],
                    },
                    ensure_ascii=True,
                )
            )
            if idx >= 5:
                break
        return "\n".join(lines)

    @staticmethod
    def _fallback_answer(message: str, retrievals: list[dict]) -> str:
        if not retrievals:
            return "I don't have grounded context for that yet."
        lead = retrievals[0]
        if "availability" in message.lower() or "book" in message.lower():
            return "I can share the live booking page if you want to schedule an interview."
        return f"Based on {lead['source_name']}: {lead['excerpt']}"

    @staticmethod
    def _booking_answer(message: str, calendar_context: dict) -> str | None:
        lowered = message.lower()
        if not any(keyword in lowered for keyword in ("availability", "available", "book", "schedule", "slot", "meeting", "interview")):
            return None

        booking_url = calendar_context.get("booking_url")
        if booking_url:
            return (
                "You can book time with me directly here: "
                f"{booking_url} . "
                "That page shows the live interview slots and confirms the meeting end to end."
            )

        message = calendar_context.get("message")
        if message:
            return message
        return "Booking is not configured right now."
