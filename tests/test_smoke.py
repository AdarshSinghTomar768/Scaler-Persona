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
