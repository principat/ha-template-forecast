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

import os
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


def _wait_until_serving(base_url: str, proc: subprocess.Popen, timeout: float = 300) -> None:
    # generous: on a fresh Python environment Home Assistant first installs the requirements of
    # the integrations it loads, which can take minutes (later runs start in seconds)
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

    # set E2E_HASS_LOG=<file> to keep the output of hass when debugging a failing run
    log_path = os.environ.get("E2E_HASS_LOG")
    log = open(log_path, "w") if log_path else subprocess.DEVNULL
    proc = subprocess.Popen(["hass", "-c", str(config_dir)], stdout=log, stderr=log)
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

    # Location, then analytics/integration steps - all just "Next", finished with "Finish".
    # The number of steps has changed across HA versions, so keep clicking "Next" until
    # "Finish" shows up. On a fresh Python environment Home Assistant installs missing
    # integration requirements at first boot, which can take minutes while the onboarding
    # shows "Waiting for Home Assistant to finish starting up" and keeps "Next" disabled -
    # so poll for an enabled button instead of using short click timeouts.
    finish = page.get_by_role("button", name="Finish")
    next_button = page.get_by_role("button", name="Next")
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline and not finish.is_visible():
        if next_button.count() and next_button.first.is_enabled():
            next_button.first.click()
            page.wait_for_timeout(500)
        else:
            page.wait_for_timeout(500)
    finish.click(timeout=10000)
    try:
        page.wait_for_url("**/home/overview", timeout=120000)  # slow on a cold start
    except Exception:
        # CI uploads tests_e2e/screenshots/*.png - makes onboarding failures diagnosable
        page.screenshot(path=str(REPO_ROOT / "tests_e2e/screenshots/onboarding_failure.png"))
        raise

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
