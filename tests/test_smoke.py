"""Smoke test of the main flow with the external APIs mocked.
Run from the project root:  pytest -q
Uses a throw-away SQLite file, so it never touches your Supabase database."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_student_guide.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, engine
from app.main import app
from app.services import groq_service


def fake_chat_json(system, user, temperature=0.4, max_tokens=4000):
    if "roadmap" in user.lower():
        return {"steps": [{"topic": f"Topic {i}", "why": "because", "concepts": ["a", "b"],
                           "after_learning": "build", "project_idea": "proj", "practice_task": "practice",
                           "expected_outcome": "outcome", "search_query": f"topic {i} tutorial"}
                          for i in range(1, 6)]}
    return {"title": "Write one SQL query", "description": "Do it.", "difficulty": "easy"}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(groq_service, "chat_json", fake_chat_json)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def register(client, email="a@example.com", college="Test College"):
    return client.post("/api/auth/register", json={
        "name": "Asha", "email": email, "password": "password123", "college": college,
        "career_role": "Backend Developer"})


def test_auth_required(client):
    assert client.get("/api/progress").status_code == 401
    assert client.get("/dashboard", follow_redirects=False).status_code == 303


def test_register_login_logout(client):
    r = register(client)
    assert r.status_code == 201 and "password" not in r.text
    assert client.get("/api/auth/me").json()["email"] == "a@example.com"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"}).status_code == 200


def test_roadmap_and_progress(client):
    register(client)
    r = client.post("/api/roadmap/generate", json={})
    assert r.status_code == 201
    steps = r.json()["steps"]
    assert len(steps) == 5 and steps[0]["status"] == "in_progress"
    done = client.post(f"/api/roadmap/steps/{steps[0]['id']}/complete").json()
    assert done["completed_steps"] == 1 and done["percent"] == 20
    assert client.get("/api/progress").json()["roadmap"]["completed_steps"] == 1


def test_users_cannot_touch_each_others_data(client):
    register(client, "a@example.com")
    step_id = client.post("/api/roadmap/generate", json={}).json()["steps"][0]["id"]
    client.post("/api/auth/logout")
    register(client, "b@example.com")
    assert client.post(f"/api/roadmap/steps/{step_id}/complete").status_code == 404


def test_daily_task_is_reused(client):
    register(client)
    first = client.get("/api/tasks/today").json()
    assert client.get("/api/tasks/today").json()["id"] == first["id"]
    assert client.post(f"/api/tasks/{first['id']}/complete").json()["completed"] is True


def test_community_same_college(client):
    register(client, "a@example.com", "Alpha College")
    client.post("/api/auth/logout")
    register(client, "b@example.com", "Alpha College")
    client.post("/api/community/posts", json={"type": "question", "title": "Hello", "body": "How to start?"})
    assert len(client.get("/api/community/users").json()) == 1
    assert len(client.get("/api/community/posts").json()) == 1
