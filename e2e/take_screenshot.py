"""Regenerates docs/screenshot.png: starts a throw-away app, adds sample data and captures the UI.

    cd e2e && ../.venv-e2e/bin/python take_screenshot.py
"""
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from conftest import PROJECT_DIR, running_app

OUTPUT = PROJECT_DIR / "docs" / "screenshot.png"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp, running_app(Path(tmp)) as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="light", device_scale_factor=2)
        page.goto(f"{url}/index.html")
        expect(page.locator("#live")).to_have_text("live")

        page.request.post(f"{url}/api/testing/sample-events")
        soon = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
        page.request.post(f"{url}/api/events", headers={"Content-Type": "application/json"}, data=json.dumps({
            "title": "Pyronaut workshop", "start": soon.isoformat(), "end": (soon + timedelta(hours=2)).isoformat(),
            "location": "Prague", "reminder_minutes": 15, "description": "Micronaut features tour",
        }))
        page.reload()
        expect(page.locator("#live")).to_have_text("live")
        expect(page.locator("#grid .ev").first).to_be_visible()
        page.get_by_role("button", name="🧪 Testing").click()
        page.get_by_role("menuitem", name="Show a reminder for the next event").click()
        expect(page.locator("#toasts .toast.reminder")).to_be_visible()
        page.mouse.move(0, 0)

        OUTPUT.parent.mkdir(exist_ok=True)
        page.screenshot(path=OUTPUT, clip={"x": 0, "y": 0, "width": 1440, "height": 1000})
        browser.close()
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
