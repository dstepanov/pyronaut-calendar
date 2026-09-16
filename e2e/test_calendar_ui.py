import json
import re
import uuid
from datetime import datetime, timedelta

from playwright.sync_api import Page, expect


def unique(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def local(value: datetime) -> str:
    """The format <input type=datetime-local> and the API use."""
    return value.strftime("%Y-%m-%dT%H:%M")


def today_at(hour: int, minute: int = 0) -> datetime:
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)


def fill_event(page: Page, title: str, start: datetime, end: datetime, *, location: str = "",
               category: str | None = None, reminder: str | None = None, description: str = "") -> None:
    dialog = page.locator("#dlg")
    dialog.get_by_label("Title", exact=True).fill(title)
    dialog.get_by_label("Start", exact=True).fill(local(start))
    dialog.get_by_label("End", exact=True).fill(local(end))
    dialog.get_by_label("Location", exact=True).fill(location)
    dialog.get_by_label("Description", exact=True).fill(description)
    if category is not None:
        dialog.get_by_label("Category", exact=True).select_option(label=category)
    if reminder is not None:
        dialog.get_by_label("Reminder", exact=True).select_option(label=reminder)


def create_event(page: Page, title: str, start: datetime, end: datetime, **fields) -> None:
    page.get_by_role("button", name="+ New event").click()
    expect(page.locator("#formTitle")).to_have_text("New event")
    fill_event(page, title, start, end, **fields)
    page.locator("#dlg").get_by_role("button", name="Save").click()
    expect(page.locator("#dlg")).to_be_hidden()


def list_row(page: Page, title: str):
    return page.locator("#list .row", has_text=title)


def toast(page: Page, text: str):
    return page.locator("#toasts .toast", has_text=text)


def test_page_loads_with_categories_and_live_connection(calendar: Page):
    expect(calendar).to_have_title("Pyronaut Calendar")
    expect(calendar.locator("#appName")).to_have_text("📅 Pyronaut Calendar")
    for name in ("Family", "Health", "Personal", "Work"):
        expect(calendar.locator("#cats .cat", has_text=name)).to_be_visible()
    expect(calendar.locator("#title")).to_have_text(datetime.now().strftime("%B %Y"))
    expect(calendar.locator("#grid .day.today")).to_have_count(1)


def test_create_event_shows_everywhere(calendar: Page):
    title = unique("Standup")
    create_event(calendar, title, today_at(9), today_at(9, 15), location="Room 1",
                 category="Work", reminder="15 minutes before")

    expect(toast(calendar, f"Added “{title}”")).to_be_visible()
    row = list_row(calendar, title)
    expect(row).to_contain_text("Work")
    expect(row).to_contain_text("Room 1")
    expect(row).to_contain_text("⏰ 15 min")
    expect(calendar.locator("#grid .day.today .ev", has_text=title)).to_be_visible()
    expect(calendar.locator("#agenda")).to_contain_text(f"09:00–09:15  {title} @ Room 1 [Work]")


def test_edit_event(calendar: Page):
    title = unique("Retro")
    create_event(calendar, title, today_at(11), today_at(12), category="Work")

    list_row(calendar, title).click()
    dialog = calendar.locator("#dlg")
    expect(calendar.locator("#formTitle")).to_have_text("Edit event")
    expect(dialog.get_by_label("Title", exact=True)).to_have_value(title)
    expect(dialog.get_by_label("Category", exact=True)).to_have_value(re.compile(r"\d+"))

    renamed = f"{title} (moved)"
    fill_event(calendar, renamed, today_at(13), today_at(14), location="Room 7", category="Personal")
    dialog.get_by_role("button", name="Save").click()

    expect(toast(calendar, f"Updated “{renamed}”")).to_be_visible()
    row = list_row(calendar, renamed)
    expect(row).to_contain_text("Personal")
    expect(row).to_contain_text("Room 7")
    expect(calendar.locator("#agenda")).to_contain_text(f"13:00–14:00  {renamed} @ Room 7 [Personal]")


def test_delete_event(calendar: Page):
    title = unique("Dentist")
    create_event(calendar, title, today_at(16), today_at(17))
    expect(list_row(calendar, title)).to_be_visible()

    list_row(calendar, title).click()
    calendar.locator("#dlg").get_by_role("button", name="Delete").click()

    expect(calendar.locator("#dlg")).to_be_hidden()
    expect(toast(calendar, f"Removed “{title}”")).to_be_visible()
    expect(list_row(calendar, title)).to_have_count(0)
    expect(calendar.locator("#grid .ev", has_text=title)).to_have_count(0)


def test_new_event_dialog_uses_configured_defaults_and_can_be_cancelled(calendar: Page):
    calendar.get_by_role("button", name="+ New event").click()
    dialog = calendar.locator("#dlg")
    expect(dialog.get_by_label("Reminder", exact=True)).to_have_value("15")
    start = datetime.fromisoformat(dialog.get_by_label("Start", exact=True).input_value())
    end = datetime.fromisoformat(dialog.get_by_label("End", exact=True).input_value())
    assert end - start == timedelta(minutes=60)

    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).to_be_hidden()


def test_validation_errors_are_shown_in_the_dialog(calendar: Page):
    calendar.get_by_role("button", name="+ New event").click()
    dialog = calendar.locator("#dlg")
    fill_event(calendar, unique("Backwards"), today_at(10), today_at(9))
    dialog.get_by_role("button", name="Save").click()
    expect(calendar.locator("#err")).to_have_text("End must not be before start.")
    expect(dialog).to_be_visible()

    # server-side validation (@NotBlank) is reported too
    fill_event(calendar, "   ", today_at(9), today_at(10))
    calendar.evaluate("document.querySelector('#dlg input[name=title]').removeAttribute('required')")
    dialog.get_by_role("button", name="Save").click()
    expect(calendar.locator("#err")).to_contain_text("must not be blank")
    dialog.get_by_role("button", name="Cancel").click()


def test_clicking_a_day_prefills_the_date_and_selects_the_agenda_day(calendar: Page):
    day = calendar.locator("#grid .day:not(.other)").filter(has=calendar.locator(".num", has_text=re.compile(r"^10$")))
    day.click(position={"x": 5, "y": 5})
    month = datetime.now().strftime("%Y-%m")
    expect(calendar.locator("#dlg").get_by_label("Start", exact=True)).to_have_value(f"{month}-10T09:00")
    expect(calendar.locator("#agendaDay")).to_have_value(f"{month}-10")
    calendar.locator("#dlg").get_by_role("button", name="Cancel").click()


def test_categories_can_be_added_filtered_and_deleted(calendar: Page):
    name = unique("Travel")
    calendar.get_by_placeholder("New category").fill(name)
    calendar.locator("#catForm").get_by_role("button", name="Add").click()
    expect(toast(calendar, f"New category “{name}”")).to_be_visible()
    category = calendar.locator("#cats .cat", has_text=name)
    expect(category).to_be_visible()

    trip = unique("Trip")
    other = unique("Not a trip")
    create_event(calendar, trip, today_at(7), today_at(8), category=name)
    create_event(calendar, other, today_at(8), today_at(9))

    category.click()
    expect(category).to_have_class(re.compile("selected"))
    expect(list_row(calendar, trip)).to_be_visible()
    expect(list_row(calendar, other)).to_have_count(0)

    calendar.locator("#cats .cat", has_text="All categories").click()
    expect(list_row(calendar, other)).to_be_visible()

    category.hover()
    category.get_by_role("button", name="✕").click()
    expect(toast(calendar, f"Deleted category “{name}”")).to_be_visible()
    expect(category).to_have_count(0)
    # the event is kept, without a category
    expect(list_row(calendar, trip)).to_be_visible()
    expect(list_row(calendar, trip).locator(".tag")).to_have_count(0)


def test_duplicate_category_is_rejected(calendar: Page):
    calendar.get_by_placeholder("New category").fill("Work")
    calendar.locator("#catForm").get_by_role("button", name="Add").click()
    expect(toast(calendar, "Category 'Work' already exists")).to_be_visible()


def test_search_is_paginated(calendar: Page):
    tag = uuid.uuid4().hex[:8]
    for i in range(7):
        create_event(calendar, f"Search {tag} #{i}", today_at(18, i), today_at(18, i + 1))

    calendar.get_by_placeholder("Title or description…").fill(tag)
    results = calendar.locator("#results .row")
    expect(calendar.locator("#searchInfo")).to_have_text("7 matches")
    expect(results).to_have_count(5)
    expect(calendar.locator("#pgInfo")).to_have_text("Page 1 of 2")
    expect(calendar.get_by_role("button", name="‹ Prev")).to_be_disabled()

    calendar.get_by_role("button", name="Next ›").click()
    expect(calendar.locator("#pgInfo")).to_have_text("Page 2 of 2")
    expect(results).to_have_count(2)
    expect(calendar.get_by_role("button", name="Next ›")).to_be_disabled()

    results.first.click()
    expect(calendar.locator("#formTitle")).to_have_text("Edit event")
    calendar.locator("#dlg").get_by_role("button", name="Cancel").click()

    calendar.get_by_placeholder("Title or description…").fill("")
    expect(calendar.locator("#searchSection")).to_be_hidden()


def test_week_view_and_navigation(calendar: Page):
    this_month = datetime.now().strftime("%B %Y")
    calendar.get_by_role("button", name="Week").click()
    expect(calendar.locator("#grid")).to_have_class(re.compile("week"))
    expect(calendar.locator("#grid .day")).to_have_count(7)

    calendar.get_by_role("button", name="Month").click()
    expect(calendar.locator("#grid .day")).to_have_count(42)

    calendar.get_by_role("button", name="Next").click()
    expect(calendar.locator("#title")).not_to_have_text(this_month)
    calendar.get_by_role("button", name="Today").click()
    expect(calendar.locator("#title")).to_have_text(this_month)


def test_changes_from_another_client_arrive_live(calendar: Page, base_url: str):
    title = unique("Pushed")
    start = today_at(20)
    response = calendar.request.post(f"{base_url}/api/events", data=json.dumps({
        "title": title, "start": local(start) + ":00", "end": local(start + timedelta(hours=1)) + ":00",
    }), headers={"Content-Type": "application/json"})
    assert response.status == 201

    # no reload: the WebSocket message triggers the refresh
    expect(toast(calendar, f"Added “{title}”")).to_be_visible()
    expect(list_row(calendar, title)).to_be_visible()

    event_id = response.json()["id"]
    assert calendar.request.delete(f"{base_url}/api/events/{event_id}").status == 204
    expect(toast(calendar, f"Removed “{title}”")).to_be_visible()
    expect(list_row(calendar, title)).to_have_count(0)


def test_reminder_is_pushed_to_the_browser(calendar: Page):
    title = unique("Call")
    start = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=3)
    create_event(calendar, title, start, start + timedelta(minutes=30), location="Zoom", reminder="5 minutes before")

    reminder = calendar.locator("#toasts .toast.reminder", has_text=title)
    expect(reminder).to_be_visible(timeout=20_000)
    expect(reminder).to_have_text(re.compile(rf"⏰ {re.escape(title)} starts in \d minutes? at Zoom"))


def test_export_downloads_an_icalendar_file(calendar: Page):
    title = unique("Exported")
    create_event(calendar, title, today_at(15), today_at(16), description="Bring slides", reminder="30 minutes before")

    with calendar.expect_download() as download_info:
        calendar.get_by_role("link", name="⬇ Export .ics").click()
    download = download_info.value
    assert download.suggested_filename == "calendar.ics"
    body = open(download.path(), encoding="utf-8").read()
    assert body.startswith("BEGIN:VCALENDAR")
    assert f"SUMMARY:{title}" in body
    assert "DESCRIPTION:Bring slides" in body
    assert "TRIGGER:-PT30M" in body


def test_swagger_ui_lists_the_api(calendar: Page, base_url: str):
    with calendar.context.expect_page() as popup_info:
        calendar.get_by_role("link", name="API docs (Swagger UI)").click()
    docs = popup_info.value
    expect(docs.get_by_text("Pyronaut Calendar API")).to_be_visible()
    expect(docs.locator(".opblock-summary-path", has_text="/api/events/agenda")).to_be_visible()
