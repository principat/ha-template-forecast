"""Fixtures for the real-browser / real-HA-instance UI rendering tests.

Unlike tests/ (which mocks Home Assistant entirely via
pytest-homeassistant-custom-component), these tests boot an actual `hass`
process - complete with the real `home-assistant-frontend` static assets -
and drive it with a real headless Chromium via Playwright. That's the only
way to see how a config-flow description *actually renders* (line
wrapping, the collapsed "Info & examples" widget, ICU MessageFormat
parsing, a real placeholder substitution). tests/test_translations.py
checks that the underlying JSON is well-formed but never looks at the
rendered DOM - this suite does.

This is deliberately kept out of the default `pytest` run (see
tests_e2e/pytest.ini): it needs `home-assistant-frontend` and a Chromium
download (`playwright install chromium`), and a full onboarding-plus-boot
cycle takes several seconds, which is wasted cost on every quick unit-test
iteration. Run it explicitly with `pytest tests_e2e`.
"""
from __future__ import annotations

import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ONBOARDING_NAME = "E2E"
ONBOARDING_USERNAME = "e2e"
ONBOARDING_PASSWORD = "e2e-test-password-1234"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_serving(base_url: str, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"hass exited early with code {proc.returncode}")
        try:
            urllib.request.urlopen(base_url, timeout=1)
            return
        except urllib.error.URLError:
            time.sleep(0.5)
    raise TimeoutError(f"hass never came up on {base_url} within {timeout}s")


@pytest.fixture(scope="session")
def ha_base_url():
    """Boot a real, throwaway Home Assistant instance for the whole test session.

    Uses a minimal configuration.yaml (http/frontend/config/lovelace/sun) -
    not `default_config:` - so startup stays fast and log noise stays low;
    `sun:` exists solely to give the Transform-mode flow a real source
    entity to pick in its EntitySelector.
    """
    port = _free_port()
    config_dir = Path(tempfile.mkdtemp(prefix="ha_e2e_config_"))
    (config_dir / "custom_components").symlink_to(
        REPO_ROOT / "custom_components", target_is_directory=True
    )
    (config_dir / "configuration.yaml").write_text(
        f"http:\n  server_port: {port}\nfrontend:\nconfig:\nlovelace:\nsun:\n"
    )

    proc = subprocess.Popen(
        ["hass", "-c", str(config_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_serving(base_url, proc)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(config_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def authenticated_storage_state(ha_base_url, browser):
    """Run onboarding once per session, return a Playwright storage_state path.

    Onboarding (create user -> location -> analytics -> integrations ->
    finish) is the same one-time wizard a real install shows on first boot;
    automating it here is exactly the manual step the whole point of this
    suite is to remove. Every test then reuses the resulting session cookie
    instead of onboarding again.
    """
    page = browser.new_page()
    page.goto(ha_base_url, wait_until="networkidle")
    page.get_by_role("button", name="Create my smart home").click()
    page.locator("input[name=name]").fill(ONBOARDING_NAME)
    page.locator("input[name=username]").fill(ONBOARDING_USERNAME)
    page.locator("input[name=password]").fill(ONBOARDING_PASSWORD)
    page.locator("input[name=password_confirm]").fill(ONBOARDING_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_timeout(1000)

    # Location, then analytics/integration steps - all just "Next", finished
    # with "Finish". Number of intermediate steps has changed across HA
    # versions, so keep clicking "Next" until it's gone rather than hardcoding
    # a step count.
    page.get_by_role("button", name="Next").click()
    for _ in range(5):
        try:
            page.get_by_role("button", name="Next").click(timeout=2000)
        except Exception:
            break
    page.get_by_role("button", name="Finish").click(timeout=5000)
    page.wait_for_url("**/home/overview", timeout=10000)

    # Our fixture picks a random http server_port per run, which differs
    # from the 8123 Home Assistant expects by default - it treats that as a
    # network-config change on first boot and blocks the UI behind a
    # "Confirm new HTTP server configuration" safety dialog until dismissed.
    try:
        page.get_by_role("button", name="Confirm").click(timeout=5000)
    except Exception:
        pass

    state_dir = tempfile.mkdtemp(prefix="ha_e2e_state_")
    state_path = Path(state_dir) / "storage_state.json"
    page.context.storage_state(path=str(state_path))
    page.close()
    yield str(state_path)
    shutil.rmtree(state_dir, ignore_errors=True)


@pytest.fixture
def browser_context_args(browser_context_args, authenticated_storage_state, ha_base_url):
    return {
        **browser_context_args,
        "storage_state": authenticated_storage_state,
        "base_url": ha_base_url,
    }
