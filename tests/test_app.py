import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from ngui.app import signal_app
from ngui.config import Config, Home

ROOT = Path(__file__).parent.parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _is_up(url: str) -> bool:
    """True once the server answers HTTP at all (the full boot has no "/" page: 404)."""
    try:
        urlopen(url + "/", timeout=1).close()
        return True
    except HTTPError:
        return True
    except (URLError, OSError):
        return False


def _wait(cond, timeout=20.0) -> None:
    deadline = time.monotonic() + timeout
    while not cond():
        if time.monotonic() > deadline:
            raise TimeoutError("condition not met")
        time.sleep(0.05)


@pytest.fixture
def start_app(tmp_path):
    procs = []
    log_path = tmp_path / "app.log"

    def start(env: dict[str, str]):
        port = _free_port()
        full = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
        full.update(env, NGUI_PORT=str(port))
        with log_path.open("ab") as log:
            proc = subprocess.Popen([sys.executable, "-m", "ngui", "run"], cwd=ROOT, env=full,
                                    stdout=log, stderr=subprocess.STDOUT)
        procs.append(proc)
        url = f"http://127.0.0.1:{port}"
        try:
            _wait(lambda: proc.poll() is not None or _is_up(url))
        except TimeoutError:
            pass
        assert proc.poll() is None and _is_up(url), (
            f"app failed to start; output:\n{log_path.read_text(errors='replace')}")
        return proc, url

    yield start
    for proc in procs:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _get(url: str) -> str:
    with urlopen(url, timeout=5) as r:
        return r.read().decode()


def test_recovery_page_when_core_missing(tmp_path, start_app):
    proc, url = start_app({"NGUI_HOME": str(tmp_path / "h"), "NGUI_CORE_REPO": ""})
    html = _get(url + "/")
    assert "Eksik rol: storage" in html and "ngui use" in html
    assert "Eksik rol: layout" in _get(url + "/any/where")


def test_recovery_page_lists_broken_plugin(home, start_app):
    home.save_config(Config(enabled=["bad-one"]))
    bad = home.repos_dir / "bad-one"
    bad.mkdir(parents=True)
    (bad / "plugin.toml").write_text("id = = broken")
    proc, url = start_app({"NGUI_HOME": str(home.root), "NGUI_CORE_REPO": ""})
    html = _get(url + "/")
    assert "bad-one: invalid manifest" in html


def test_full_boot_with_fake_core_and_hello(home, mgr_with_core, hello_url, start_app):
    mgr_with_core.add(hello_url)
    proc, url = start_app({"NGUI_HOME": str(home.root)})
    html = _get(url + "/hello")
    assert "LAYOUT-FAKE" in html and "Merhaba dünya" in html


def test_sighup_restarts_in_place(home, mgr_with_core, start_app):
    proc, url = start_app({"NGUI_HOME": str(home.root)})
    pid = int(home.pid_path.read_text())
    assert pid == proc.pid
    assert signal_app(home) is True
    _wait(lambda: not _is_up(url))
    _wait(lambda: _is_up(url))
    assert proc.poll() is None and proc.pid == int(home.pid_path.read_text())


def test_double_sighup_during_reboot_is_not_fatal(home, mgr_with_core, start_app):
    proc, url = start_app({"NGUI_HOME": str(home.root)})
    assert signal_app(home) is True
    _wait(lambda: not _is_up(url))  # old server gone: the new image is booting
    assert signal_app(home) is True  # lands before the new handler exists
    _wait(lambda: _is_up(url))
    assert proc.poll() is None and proc.pid == int(home.pid_path.read_text())


def test_signal_app_with_stale_pid(home):
    home.root.mkdir(parents=True)
    home.pid_path.write_text("999999")
    assert signal_app(home) is False


def test_signal_app_with_garbage_pidfile(home):
    home.root.mkdir(parents=True)
    home.pid_path.write_text("not-a-pid")
    assert signal_app(home) is False


def test_signal_app_without_pidfile(home):
    assert signal_app(home) is False
