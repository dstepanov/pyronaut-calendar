import pytest
import requests

from pyronaut.test import MicronautTest, micronaut_test_fixture


@pytest.fixture
def client(request):
    fixture = micronaut_test_fixture(request, MicronautTest(environments=["test"], transactional=False))
    yield requests.with_context(fixture)
    fixture.stop()


@pytest.fixture
def disabled_client(request):
    fixture = micronaut_test_fixture(
        request,
        MicronautTest(environments=["test"], transactional=False, properties={"calendar.testing.enabled": "false"}),
    )
    yield requests.with_context(fixture)
    fixture.stop()


def test_testing_endpoints(client):
    assert client.get("/api/settings").json()["testingEnabled"] is True

    created = client.post("/api/testing/sample-events").json()["created"]
    assert created == 8
    events = client.get("/api/events").json()
    assert len(events) == 8
    assert {e["category"]["name"] for e in events if "category" in e} >= {"Work", "Personal"}

    # the reminder is only pushed: nothing is created and nothing is marked as reminded
    triggered = client.post("/api/testing/reminder").json()
    assert triggered["message"].startswith("⏰ ")
    events = client.get("/api/events").json()
    assert len(events) == 8
    assert not any(e["reminded"] for e in events)

    assert client.post("/api/testing/reset-reminders").json()["reset"] == 8

    assert client.post("/api/testing/broadcast", json={"message": "hi"}).json() == {"sent": True}
    assert client.post("/api/testing/broadcast", json={"message": ""}).status_code == 400

    response = client.post("/api/testing/random-event")
    assert response.status_code == 201
    random_event = response.json()
    assert random_event["title"]
    assert random_event["start"][:7] == random_event["created_at"][:7]  # this month
    assert random_event["end"] > random_event["start"]
    assert len(client.get("/api/events").json()) == 9

    assert client.delete("/api/testing/events").json() == {"deleted": 9}
    assert client.get("/api/events").json() == []

    # with no upcoming event the reminder is for an unsaved sample event
    sample = client.post("/api/testing/reminder").json()
    assert sample["message"] == "⏰ Sample event starts in 4 minutes at Testing menu" or \
        sample["message"] == "⏰ Sample event starts in 5 minutes at Testing menu"
    assert client.get("/api/events").json() == []


def test_testing_endpoints_can_be_disabled(disabled_client):
    assert disabled_client.get("/api/settings").json()["testingEnabled"] is False
    assert disabled_client.post("/api/testing/sample-events").status_code == 404
    assert disabled_client.post("/api/testing/random-event").status_code == 404
    assert disabled_client.delete("/api/testing/events").status_code == 404
