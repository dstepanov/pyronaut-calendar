import pytest
import requests

from pyronaut.test import MicronautTest, micronaut_test_fixture


@pytest.fixture
def my_context(request):
    fixture = micronaut_test_fixture(
        request,
        MicronautTest(environments=["test"], transactional=False),
    )
    yield fixture
    fixture.stop()


@pytest.fixture
def client(my_context):
    return requests.with_context(my_context)


def event(title="Standup", start="2026-09-16T09:00:00", end="2026-09-16T09:15:00", **extra):
    return {"title": title, "start": start, "end": end, **extra}


def create(client, **fields):
    response = client.post("/api/events", json=event(**fields))
    assert response.status_code == 201, response.text
    return response.json()


def test_event_crud(client):
    created = create(client, location="Room 1", color="#2f6fed", reminder_minutes=10)
    event_id = created["id"]
    assert created["title"] == "Standup"
    assert created["created_at"] is not None
    assert created["reminded"] is False

    response = client.get(f"/api/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["location"] == "Room 1"

    response = client.put(f"/api/events/{event_id}", json=event("Daily standup", "2026-09-16T09:30:00", "2026-09-16T09:45:00"))
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Daily standup"
    assert updated["version"] == created["version"] + 1

    response = client.get("/api/events?from=2026-09-01T00:00:00&to=2026-10-01T00:00:00")
    assert [e["title"] for e in response.json()] == ["Daily standup"]

    response = client.get("/api/events?from=2026-10-01T00:00:00&to=2026-11-01T00:00:00")
    assert response.json() == []

    assert client.delete(f"/api/events/{event_id}").status_code == 204
    assert client.get(f"/api/events/{event_id}").status_code == 404


def test_validation_and_errors(client):
    assert client.post("/api/events", json=event(title="")).status_code == 400

    response = client.post("/api/events", json=event(start="2026-09-16T10:00:00", end="2026-09-16T09:00:00"))
    assert response.status_code == 400
    assert "end must not be before" in response.json()["message"]

    response = client.post("/api/events", json=event(category={"id": 9999}))
    assert response.status_code == 400

    response = client.put("/api/events/9999", json=event())
    assert response.status_code == 404
    assert response.json()["message"] == "Event 9999 not found"

    assert client.delete("/api/events/9999").status_code == 404


def test_categories(client):
    categories = client.get("/api/categories").json()
    assert {c["name"] for c in categories} >= {"Work", "Personal"}

    response = client.post("/api/categories", json={"name": "Sport", "color": "#123456"})
    assert response.status_code == 201
    sport = response.json()

    assert client.post("/api/categories", json={"name": "Sport", "color": "#123456"}).status_code == 400
    assert client.post("/api/categories", json={"name": "Bad", "color": "red"}).status_code == 400

    # the cached list is invalidated on create
    assert "Sport" in {c["name"] for c in client.get("/api/categories").json()}

    run = create(client, title="Run", start="2026-09-17T07:00:00", end="2026-09-17T08:00:00", category={"id": sport["id"]})
    assert run["category"]["name"] == "Sport"

    filtered = client.get(f"/api/events?from=2026-09-17T00:00:00&to=2026-09-18T00:00:00&category={sport['id']}").json()
    assert [e["title"] for e in filtered] == ["Run"]

    assert client.delete(f"/api/categories/{sport['id']}").status_code == 204
    assert client.get(f"/api/events/{run['id']}").json().get("category") is None
    client.delete(f"/api/events/{run['id']}")


def test_search_is_paginated(client):
    ids = [create(client, title=f"Planning {i}", start=f"2026-11-0{i}T10:00:00", end=f"2026-11-0{i}T11:00:00")["id"] for i in range(1, 4)]
    ids.append(create(client, title="Lunch", description="planning the offsite")["id"])

    page = client.get("/api/events/search?q=PLANNING&size=2&sort=title").json()
    assert page["totalSize"] == 4
    assert len(page["content"]) == 2
    assert page["content"][0]["title"] == "Lunch"

    for event_id in ids:
        client.delete(f"/api/events/{event_id}")


def test_agenda_uses_el_templates(client):
    work = next(c for c in client.get("/api/categories").json() if c["name"] == "Work")
    ids = [
        create(client, title="Review", start="2026-12-01T14:00:00", end="2026-12-01T15:00:00",
               location="Room 2", category={"id": work["id"]})["id"],
        create(client, title="Offsite", start="2026-11-30T09:00:00", end="2026-12-02T17:00:00")["id"],
    ]

    response = client.get("/api/events/agenda?day=2026-12-01")
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert lines[0] == "Pyronaut Calendar · Tuesday, 01 December 2026 · 2 events"
    assert "(multi-day)  Offsite" in lines
    assert "14:00–15:00  Review @ Room 2 [Work]" in lines

    empty = client.get("/api/events/agenda?day=2027-01-01").text
    assert empty.strip().endswith("nothing planned")

    for event_id in ids:
        client.delete(f"/api/events/{event_id}")


def test_ical_export(client):
    created = create(client, title="Dentist, checkup", description="Bring card", reminder_minutes=30)

    response = client.get("/api/events/export.ics")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/calendar")
    body = response.text
    assert "BEGIN:VCALENDAR" in body
    assert "SUMMARY:Dentist\\, checkup" in body
    assert "DTSTART:20260916T090000" in body
    assert "TRIGGER:-PT30M" in body
    assert "DESCRIPTION:Bring card" in body

    client.delete(f"/api/events/{created['id']}")


def test_settings_and_management(client):
    settings = client.get("/api/settings").json()
    assert settings["name"] == "Pyronaut Calendar"
    assert settings["defaultDurationMinutes"] == 60

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "UP"


def test_openapi_and_ui_are_served(client):
    response = client.get("/index.html")
    assert response.status_code == 200
    assert "Pyronaut Calendar" in response.text

    spec = client.get("/swagger/calendar-0.1.0.yml")
    assert spec.status_code == 200, spec.text
    assert "/api/events" in spec.text


def test_reminder_job_marks_due_events(client):
    import time
    from datetime import datetime, timedelta

    start = (datetime.now() + timedelta(minutes=5)).replace(microsecond=0)
    due = create(client, title="Call", start=start.isoformat(), end=(start + timedelta(minutes=30)).isoformat(),
                 reminder_minutes=10)
    later = create(client, title="Later", start=(start + timedelta(hours=5)).isoformat(),
                   end=(start + timedelta(hours=6)).isoformat(), reminder_minutes=10)

    deadline = time.time() + 10
    while time.time() < deadline and not client.get(f"/api/events/{due['id']}").json()["reminded"]:
        time.sleep(0.5)

    assert client.get(f"/api/events/{due['id']}").json()["reminded"] is True
    assert client.get(f"/api/events/{later['id']}").json()["reminded"] is False

    for event_id in (due["id"], later["id"]):
        client.delete(f"/api/events/{event_id}")
