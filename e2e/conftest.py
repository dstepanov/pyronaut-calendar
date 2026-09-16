"""Fixtures for the browser tests.

By default a fresh application is started with ``pyronaut run`` in the ``e2e`` environment
(``config/application-e2e.toml``: random port, in-memory H2 database), so the tests never touch ``./data``. Pass ``--base-url http://localhost:8123`` to test an already running instance.
"""
import os
import re
import shutil
import subprocess
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PYRONAUT = Path.home() / ".pyenv/versions/graalpy3.13-25.3.4.1/bin/pyronaut"
STARTUP_TIMEOUT_SECONDS = 240

expect.set_options(timeout=15_000)


def _pyronaut() -> str:
    found = os.environ.get("PYRONAUT") or shutil.which("pyronaut")
    if found:
        return found
    if DEFAULT_PYRONAUT.exists():
        return str(DEFAULT_PYRONAUT)
    pytest.exit("pyronaut CLI not found: put it on PATH or set PYRONAUT=/path/to/pyronaut", returncode=2)


def _wait_until_up(process: subprocess.Popen, log: Path) -> str:
    """Waits for Micronaut's "Server Running: <url>" line, then for /health to answer."""
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    url = None
    while time.time() < deadline:
        if process.poll() is not None:
            pytest.exit(f"pyronaut run exited with {process.returncode}; see {log}", returncode=3)
        if url is None:
            match = re.search(r"Server Running: (http://\S+)", log.read_text(errors="replace"))
            url = match and match.group(1).rstrip("/")
        if url:
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=2) as response:
                    if response.status == 200:
                        return url
            except OSError:
                pass
        time.sleep(1)
    process.terminate()
    pytest.exit(f"application did not start within {STARTUP_TIMEOUT_SECONDS}s; see {log}", returncode=3)


@contextmanager
def running_app(log_dir: Path):
    """Starts ``pyronaut run`` in the e2e environment and yields its base URL; stops it on exit."""
    log = log_dir / "pyronaut-run.log"
    env = dict(os.environ, MICRONAUT_ENVIRONMENTS="e2e")
    graalpy_venv = PROJECT_DIR / ".venv"
    if graalpy_venv.exists():
        env["VIRTUAL_ENV"] = str(graalpy_venv)
        env["PATH"] = f"{graalpy_venv / 'bin'}{os.pathsep}{env['PATH']}"

    with log.open("w") as out:
        process = subprocess.Popen(
            [_pyronaut(), "run"], cwd=PROJECT_DIR, env=env, stdout=out, stderr=subprocess.STDOUT
        )
    try:
        yield _wait_until_up(process, log)
    finally:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def base_url(request, tmp_path_factory):
    configured = request.config.getoption("base_url")
    if configured:
        yield configured.rstrip("/")
        return
    with running_app(tmp_path_factory.mktemp("app")) as url:
        yield url


@pytest.fixture
def calendar(page: Page, base_url: str) -> Page:
    """The calendar page, loaded, with its WebSocket connected."""
    # confirm() for deletes, prompt() in the Testing menu: accept with the prompt's default text
    page.on("dialog", lambda dialog: dialog.accept(dialog.default_value))
    page.goto(f"{base_url}/index.html")
    expect(page.locator("#live")).to_have_text("live")
    expect(page.locator("#cats")).to_contain_text("Work")
    return page
