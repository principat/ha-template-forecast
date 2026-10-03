"""Driver for REQ 2.8 (Forecast Chart dashboard card).

The card is TypeScript running in the browser, so these scenarios cannot use Home Assistant
internals like ``driver.py`` does. Instead they run the card's platform independent logic
(auto-detection, editor <-> stored configuration mapping, series building) in Node through the
small JSON bridge ``frontend/acceptance/bridge.ts``. What this deliberately does not cover - the
look of the chart and the editor widgets inside a real Home Assistant frontend - is checked by
``tests_e2e/test_forecast_chart_card.py``.

Like ``driver.py`` this is the single seam for its feature file: feature files and steps only
call methods on :class:`CardDriver`.

Requirements: Node.js and ``npm ci`` in ``frontend/``. Without them the card scenarios are
skipped locally; when the ``CI`` environment variable is set they fail instead, so the CI can
never silently skip them.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
_bundle_path: Path | None = None


def _unavailable(message: str) -> None:
    if os.environ.get("CI"):
        raise RuntimeError(message)
    pytest.skip(message)


def _bridge_bundle() -> Path:
    """Bundle the bridge once per test session and return the path of the result."""
    global _bundle_path
    if _bundle_path is not None and _bundle_path.exists():
        return _bundle_path
    node, npx = shutil.which("node"), shutil.which("npx")
    if not node or not npx or not (FRONTEND / "node_modules").is_dir():
        _unavailable(
            "REQ 2.8 scenarios need Node.js and 'npm ci' in frontend/ (see tests_acceptance/README.md)"
        )
    out = Path(tempfile.mkdtemp(prefix="card_bridge_")) / "bridge.mjs"
    subprocess.run(
        [
            npx,
            "--no-install",
            "esbuild",
            "acceptance/bridge.ts",
            "--bundle",
            "--format=esm",
            "--platform=node",
            f"--outfile={out}",
            "--log-level=error",
        ],
        cwd=FRONTEND,
        check=True,
    )
    _bundle_path = out
    return out


class CardDriver:
    """Plays the roles of the card editor user and of Home Assistant's entity states."""

    NOW = "2026-10-02T10:30:00+00:00"

    def __init__(self) -> None:
        self.states: dict[str, dict[str, Any]] = {}
        self.config: dict[str, Any] = {"type": "custom:forecast-chart-card", "sources": []}
        self.now = self.NOW
        self.opened_with: dict[str, Any] | None = None
        self.shown: dict[str, Any] | None = None

    # ---- the bridge ------------------------------------------------------------
    def _call(self, request: dict[str, Any]) -> Any:
        node = shutil.which("node")
        done = subprocess.run(
            [node, str(_bridge_bundle())],
            input=json.dumps({**request, "states": self.states}),
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    # ---- the outside world -------------------------------------------------------
    def set_entity(
        self,
        entity_id: str,
        attribute: str,
        items: list[dict[str, Any]],
        unit: str | None = None,
    ) -> None:
        attributes: dict[str, Any] = {attribute: items}
        if unit:
            attributes["unit_of_measurement"] = unit
        self.states[entity_id] = {"state": "ok", "attributes": attributes}

    # ---- editor ---------------------------------------------------------------------
    def load_config(self, config: dict[str, Any]) -> None:
        """A card that was configured and saved earlier is opened again."""
        self.config = {"type": "custom:forecast-chart-card", **copy.deepcopy(config)}

    def open_editor(self) -> None:
        """Open the editor for the first source: it only reads, it must not change anything."""
        self.opened_with = copy.deepcopy(self.stored_source(0))
        self.shown = self.form(0)

    def add_source(self, entity: str | None = None) -> int:
        """'Add entity' in the editor, optionally followed by picking the entity."""
        self.config["sources"].append({"entity": ""})
        index = len(self.config["sources"]) - 1
        if entity:
            self.choose_entity(index, entity)
        return index

    def move_source(self, index: int, delta: int) -> None:
        sources = self.config["sources"]
        sources[index], sources[index + delta] = sources[index + delta], sources[index]

    def remove_source(self, index: int) -> None:
        del self.config["sources"][index]

    def form(self, index: int = 0) -> dict[str, Any]:
        """What the editor shows for a source: selections plus the available choices."""
        return self._call({"command": "form", "source": self.config["sources"][index]})

    def _apply(self, index: int, next_form: dict[str, Any]) -> None:
        self.config["sources"][index] = self._call(
            {
                "command": "apply",
                "source": self.config["sources"][index],
                "next_form": next_form,
            }
        )

    def choose_entity(self, index: int, entity: str) -> None:
        form = self.form(index)["form"]
        self._apply(index, {**form, "entity": entity})

    def choose_attribute(self, index: int, attribute: str) -> None:
        form = self.form(index)["form"]
        self._apply(index, {**form, "attribute": attribute})

    def add_value_field(self, index: int, key: str) -> None:
        form = self.form(index)["form"]
        self._apply(index, {**form, "extra_keys": [*form["extra_keys"], key]})

    def set_detail(self, index: int, key: str, **detail: Any) -> None:
        """Change settings in the 'Details' section of one value field."""
        form = self.form(index)["form"]
        slot = ([form["value_key"], *form["extra_keys"]]).index(key)
        name = f"detail_{slot}"
        self._apply(index, {**form, name: {**form[name], **detail}})

    # ---- result ------------------------------------------------------------------------
    def stored_source(self, index: int = 0) -> dict[str, Any]:
        return self.config["sources"][index]

    def series(self) -> dict[str, Any]:
        return self._call({"command": "series", "config": self.config, "now": self.now})

    def line(self, name: str) -> dict[str, Any]:
        lines = [s for s in self.series()["series"] if s["name"] == name]
        assert len(lines) == 1, f"expected one line named {name!r}, got {len(lines)}"
        return lines[0]

    @staticmethod
    def hex_to_rgb(color: str) -> list[int]:
        value = color.lstrip("#")
        return [int(value[i : i + 2], 16) for i in (0, 2, 4)]
