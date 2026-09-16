"""The Testing menu. Runs after test_calendar_ui.py because "Delete all events" wipes the shared database."""
import json
import re
from datetime import datetime, timedelta

from playwright.sync_api import Page, expect


def choose(page: Page, item: str) -> None:
    page.get_by_role("button", name="🧪 Testing").click()
    page.get_by_role("menuitem", name=item).click()


def test_menu_lists_the_testing_actions(calendar: Page):
    calendar.get_by_role("button", name="🧪 Testing").click()
    items = calendar.get_by_role("menuitem")
    expect(items).to_have_text([
        "Add a random event",
        "Add sample week of events",
        "Show a reminder for the next event",
        "Run reminder job",
        "Reset reminder flags",
        "Broadcast a notification…",
        "Delete all events",
    ])
    calendar.locator("#grid").click(position={"x": 1, "y": 1})  # click outside closes it
    expect(items.first).to_be_hidden()


def test_random_event_is_added(calendar: Page, base_url: str):
    before = len(calendar.request.get(f"{base_url}/api/events").json())
    with calendar.expect_response("**/api/testing/random-event") as response_info:
        choose(calendar, "Add a random event")
    created = response_info.value.json()
    expect(calendar.locator("#toasts .toast", has_text=f"Added “{created['title']}”").first).to_be_visible()
    expect(calendar.locator(f"#grid .ev[title='{created['title']}']").first).to_be_visible()
    assert len(calendar.request.get(f"{base_url}/api/events").json()) == before + 1


def test_sample_events_fill_the_current_week(calendar: Page):
    choose(calendar, "Add sample week of events")
    expect(calendar.locator("#toasts .toast", has_text="Created 8 sample events this week")).to_be_visible()
    calendar.get_by_role("button", name="Week").click()
    for title in ("Team standup", "Sprint planning", "Morning run", "Architecture review", "Hiking trip"):
        expect(calendar.locator("#grid .ev", has_text=title).first).to_be_visible()


def test_show_reminder_for_the_next_event_changes_nothing(calendar: Page, base_url: str):
    before = calendar.request.get(f"{base_url}/api/events").json()
    upcoming = sorted((e for e in before if e["start"] >= datetime.now().isoformat()), key=lambda e: e["start"])
    expected = upcoming[0]["title"] if upcoming else "Sample event"

    choose(calendar, "Show a reminder for the next event")
    expect(calendar.locator("#toasts .toast.reminder", has_text=f"⏰ {expected} starts")).to_be_visible()
    assert calendar.request.get(f"{base_url}/api/events").json() == before


def test_reset_and_rerun_reminders(calendar: Page, base_url: str):
    start = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=3)
    title = f"Due {start:%H%M%S}-{datetime.now():%f}"
    response = calendar.request.post(f"{base_url}/api/events", data=json.dumps({
        "title": title, "start": start.isoformat(), "end": (start + timedelta(minutes=30)).isoformat(),
        "reminder_minutes": 5,
    }), headers={"Content-Type": "application/json"})
    assert response.status == 201

    # sent by this run or by the scheduled job, whichever comes first
    choose(calendar, "Run reminder job")
    expect(calendar.locator("#toasts .toast", has_text="Reminder job sent")).to_be_visible()
    expect(calendar.locator("#toasts .toast.reminder", has_text=title)).to_have_count(1)

    choose(calendar, "Reset reminder flags")
    expect(calendar.locator("#toasts .toast", has_text=re.compile(r"Reset \d+ reminder flags?"))).to_be_visible()

    # due again: reminded a second time
    choose(calendar, "Run reminder job")
    expect(calendar.locator("#toasts .toast.reminder", has_text=title)).to_have_count(2)


def test_broadcast_reaches_every_open_tab(calendar: Page, base_url: str):
    other = calendar.context.new_page()
    other.goto(f"{base_url}/index.html")
    expect(other.locator("#live")).to_have_text("live")

    # the fixture accepts the prompt with its default text
    choose(calendar, "Broadcast a notification…")
    for page in (calendar, other):
        expect(page.locator("#toasts .toast.notice", has_text="Hello from the testing menu 👋")).to_be_visible()
    other.close()


def test_delete_all_events(calendar: Page):
    expect(calendar.locator("#list .row").first).to_be_visible()
    choose(calendar, "Delete all events")
    expect(calendar.locator("#toasts .toast", has_text="Calendar cleared:")).to_be_visible()
    expect(calendar.locator("#list")).to_have_text("No events. Click a day or “New event” to add one.")
