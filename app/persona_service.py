from __future__ import annotations

import json

from .calendar_service import CalendarService
from .config import CALENDLY_SPOKEN_PATH, CALENDLY_URL, PERSONA_NAME, PERSONA_ROLE, VAPI_PHONE_NUMBER
from .knowledge import KnowledgeBase
from .openai_client import OpenAIClient


SYSTEM_PROMPT = f"""
You are {PERSONA_ROLE}.
You speak in first person on behalf of {PERSONA_NAME}, but you must clearly say you are the AI representative when asked.

Rules:
- Use only the retrieved context and the user's question.
- If the answer is supported by the sources, answer directly and confidently.
- Never mention internal phrases like "retrieved context", "provided context", "specific grounding", or "my knowledge is based on the retrieved context".
- If the answer is not supported by the sources, say briefly that you do not have enough verified information and do not guess.
- Be specific and concise.
- Mention tradeoffs when asked about projects.
- If the user asks about booking or availability, use the live booking link if one is configured.
- Do not invent projects, employers, dates, metrics, or education details.
""".strip()


VOICE_SYSTEM_PROMPT = f"""
You are the voice AI representative for {PERSONA_NAME}.

Voice behavior:
- Start by clearly saying you are Adarsh's AI representative.
- Keep responses natural, concise, and easy to understand when spoken aloud.
- Answer questions about Adarsh's background, experience, projects, skills, and fit for the role.
- If you are unsure, say you do not have grounding for that detail.
- Do not invent facts, employers, dates, metrics, or achievements.
- If the caller wants to schedule, say there is a live booking page and mention the spoken path slowly as: {CALENDLY_SPOKEN_PATH}.
- Prefer saying the spoken booking path instead of reading the full protocol like H T T P S.
- Mention that the booking page shows live availability and confirms the interview end to end.
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

        answer = self._clean_answer(answer, message, retrievals)

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
            "system_prompt": VOICE_SYSTEM_PROMPT,
            "phone_number": VAPI_PHONE_NUMBER,
            "booking_url": CALENDLY_URL,
            "spoken_booking_path": CALENDLY_SPOKEN_PATH,
            "tooling": {
                "chat_endpoint": "/api/chat",
                "availability_endpoint": "/api/availability",
                "booking_endpoint": "/api/book",
            },
            "notes": [
                "Point your Vapi or Retell assistant to these endpoints if you want backend-driven voice configuration.",
                f"Current live Vapi number: {VAPI_PHONE_NUMBER}",
                "For spoken scheduling, prefer the short Calendly path instead of reading the raw URL with protocol.",
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
            return "I don't have enough verified information to answer that confidently."
        lead = retrievals[0]
        if "availability" in message.lower() or "book" in message.lower():
            return "I can share the live booking page if you want to schedule an interview."
        excerpt = lead["excerpt"].replace("...", "").strip()
        if excerpt:
            return excerpt
        return lead["text"][:280].strip()

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

    @staticmethod
    def _clean_answer(answer: str, message: str, retrievals: list[dict]) -> str:
        lowered = answer.lower()
        meta_markers = (
            "retrieved context",
            "provided context",
            "specific grounding",
            "my knowledge is based on",
        )
        if any(marker in lowered for marker in meta_markers):
            if retrievals:
                return PersonaService._fallback_answer(message, retrievals)
            return "I don't have enough verified information to answer that confidently."
        return answer.strip()
