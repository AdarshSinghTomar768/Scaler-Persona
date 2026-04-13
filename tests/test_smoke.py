import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.knowledge import KnowledgeBase


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_knowledge_search_resume() -> None:
    kb = KnowledgeBase()
    results = kb.search("experience with rag", limit=3)
    assert results
    assert any(item["source_name"] == "Adarsh Resume" for item in results)


def test_webhook_get() -> None:
    response = client.get("/webhook")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_twilio_form() -> None:
    response = client.post(
        "/webhook",
        data={"Body": "Tell me about your RAG experience at WNS.", "From": "whatsapp:+10000000000"},
    )
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text


def test_availability_returns_booking_link() -> None:
    response = client.get("/api/availability")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"external_booking", "available"}
    assert payload.get("booking_url")


def test_booking_returns_external_booking_link() -> None:
    response = client.post(
        "/api/book",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "start_at": "2026-04-14T10:00:00Z",
            "notes": "Demo booking",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"external_booking", "confirmed"}
    assert payload.get("booking_url") or payload.get("booking_id")


def test_chat_booking_question_returns_link() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "How can I book an interview with you?", "history": []},
    )
    assert response.status_code == 200
    assert "calendly.com" in response.json()["answer"].lower()


def test_voice_config_exposes_live_number() -> None:
    response = client.get("/api/voice/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_number"] == "+1 857 269 2436"
    assert "spoken_booking_path" in payload


def test_chat_rag_question_avoids_meta_language() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Tell me about your RAG experience at WNS.", "history": []},
    )
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "retrieved context" not in answer
    assert "specific grounding" not in answer
    assert "ns global services" in answer or "wns" in answer
