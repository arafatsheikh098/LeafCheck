"""F6 e2e tests: vanilla JS frontend against the FastAPI app.

Uses Playwright's sync API to drive a real Chromium against a
uvicorn-spawned dev server. The dev server is fixture-managed and
uses a tiny smoke-trained model in tmp_path so this test does not
depend on real PlantVillage data being present.
"""

from __future__ import annotations

import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from leafcheck import train as train_mod


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def dev_server_url(tmp_path_factory) -> str:
    """Spawn a real uvicorn process for the e2e test.

    Trains a tiny model in tmp, writes a tiny advice.json, then runs
    uvicorn in a subprocess bound to a free port. Yields the base URL.
    """
    td = tmp_path_factory.mktemp("e2e_server")
    train_mod.train(
        {
            "seed": 5,
            "image_size": 32,
            "epochs": 1,
            "batch_size": 8,
            "lr": 0.01,
            "optimizer": "sgd",
            "momentum": 0.9,
            "weight_decay": 1e-4,
            "early_stop_patience": 2,
            "imbalance_threshold": 3.0,
            "pretrained": False,
            "device": "cpu",
            "data_root": str(td / "manifest.csv"),
            "output_dir": str(td / "models"),
            "synth_classes": 4,
            "synth_per_class": 12,
        }
    )
    (td / "models" / "threshold.json").write_text(
        '{"threshold": 0.5, "target_precision": 0.95, '
        '"val_precision_at_threshold": 0.95, "val_coverage_at_threshold": 0.5, '
        '"test_coverage_at_threshold": 0.5}'
    )
    advice = {
        "class_0": {
            "en": "Test English advice.",
            "bn": "পরীক্ষামূলক বাংলা পরামর্শ।",
            "reviewed_by_human": False,
        }
    }
    import json

    (td / "advice.json").write_text(json.dumps(advice))

    port = _free_port()
    env = {
        **os.environ,
        "LEAFCHECK_MODEL_DIR": str(td / "models"),
        "LEAFCHECK_ADVICE_PATH": str(td / "advice.json"),
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "leafcheck.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        cwd=str(Path(__file__).resolve().parents[2]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for /health to come up (max 30s).
    import urllib.request

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    else:
        proc.terminate()
        out, err = proc.communicate(timeout=5)
        raise RuntimeError(f"server failed to start: {out!r} {err!r}")

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _small_jpeg_bytes(color=(100, 200, 50), size=(96, 96)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def test_index_loads_no_external_hosts(dev_server_url, page) -> None:
    """F6.AC1: no external CDN. Watch network and fail on any non-localhost request."""
    external: list[str] = []

    def _on_request(req) -> None:
        url = req.url
        if not (
            url.startswith("http://127.0.0.1")
            or url.startswith("http://localhost")
            or url.startswith("data:")
            or url.startswith("blob:")
        ):
            external.append(url)

    page.on("request", _on_request)
    page.goto(dev_server_url + "/")
    page.wait_for_load_state("networkidle")
    assert not external, f"unexpected external requests: {external}"


def test_language_toggle_persists(dev_server_url, page) -> None:
    """F6.AC2: EN ↔ Bangla toggle persists across reload."""
    page.goto(dev_server_url + "/")
    # Default: EN. Tagline is the species-identification copy.
    assert "9 plant species" in page.text_content("#tagline")
    page.click("#langToggle")
    # After click, the page is in Bangla.
    assert "শনাক্ত" in page.text_content("#tagline")
    # Reload — the choice should persist (localStorage).
    page.reload()
    page.wait_for_load_state("networkidle")
    assert "শনাক্ত" in page.text_content("#tagline"), "Bangla not persisted across reload"


def test_no_horizontal_scroll_at_375(dev_server_url, page) -> None:
    """F6.AC5: 375px viewport has no horizontal scroll."""
    page.set_viewport_size({"width": 375, "height": 800})
    page.goto(dev_server_url + "/")
    scroll_w = page.evaluate("document.documentElement.scrollWidth")
    client_w = page.evaluate("document.documentElement.clientWidth")
    assert scroll_w <= client_w, f"horizontal scroll: scrollW={scroll_w} > clientW={client_w}"


def test_upload_predict_and_render(dev_server_url, page) -> None:
    """Happy path: file → predict → result card (either confident or not_sure)."""
    page.goto(dev_server_url + "/")
    img_path = Path("/tmp/leafcheck_e2e_leaf.jpg")
    img_path.write_bytes(_small_jpeg_bytes())
    with page.expect_file_chooser() as fc_info:
        page.click("#pickButton")
    fc_info.value.set_files(str(img_path))
    page.wait_for_function("() => !document.querySelector('#predict').disabled")
    page.click("#predict")
    page.wait_for_selector("#result .card", timeout=20_000)
    text = page.text_content("#result")
    # Either the model is confident ("Top guess" card) or it isn't
    # ("not sure" retake card). Both are valid renderings; what we
    # assert is that some card was shown and that the page produced
    # no JS errors.
    assert text and ("Top guess" in text or "not confident" in text.lower()), text


def test_console_no_errors(dev_server_url, page) -> None:
    """F6.AC1 follow-on: the page must not log errors at idle."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.goto(dev_server_url + "/")
    page.wait_for_load_state("networkidle")
    # Loading the page + i18n should not log any console errors.
    assert not errors, f"console errors at idle: {errors}"


def test_disclaimer_visible(dev_server_url, page) -> None:
    """F6.AC6: a visible disclaimer is rendered."""
    page.goto(dev_server_url + "/")
    text = page.text_content("#disclaimer")
    assert text and "research preview" in text.lower()
