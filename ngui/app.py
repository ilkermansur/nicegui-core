import atexit
import logging
import os
import signal
import sys
from pathlib import Path
from typing import NoReturn

from ngui import recovery
from ngui.bus import Bus, Services
from ngui.config import Home, home_from_env
from ngui.context import Kernel
from ngui.i18n import I18n
from ngui.loader import load
from ngui.manager import Manager, ManagerError

log = logging.getLogger("ngui.app")


def restart() -> NoReturn:
    # Keep SIGHUP blocked across exec (the mask survives execv) so a SIGHUP that arrives
    # while the new image boots stays pending instead of killing it (or being ignored as PID 1).
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGHUP})
    os.execv(sys.executable, [sys.executable, "-m", "ngui", "run"])


def signal_app(home: Home) -> bool:
    try:
        os.kill(int(home.pid_path.read_text().strip()), signal.SIGHUP)
    except (OSError, ValueError):
        return False
    return True


def _remove_pid(home: Home, pid: int) -> None:
    try:
        if int(home.pid_path.read_text()) == pid:
            home.pid_path.unlink()
    except (OSError, ValueError):
        pass


def run(home: Home | None = None) -> None:
    from nicegui import ui

    signal.signal(signal.SIGHUP, lambda *_: restart())
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGHUP})  # a queued SIGHUP restarts once more
    home = home or home_from_env()
    mgr = Manager(home)
    mgr.bootstrap()
    try:
        mgr.sync_deps()
    except ManagerError as e:
        log.error("dependency sync failed: %s %s", e.key, e.vars)
    sys.path.insert(0, str(home.pydeps_dir))
    cfg = home.load_config()
    i18n = I18n(cfg.default_lang)
    i18n.load("core", Path(__file__).parent / "locales")
    kernel = Kernel(home, cfg, Bus(), Services(), i18n)
    kernel.manager, kernel.restart = mgr, restart
    result = load(kernel)
    if storage := kernel.roles.get("storage"):
        i18n.lang_getter = lambda: storage.for_plugin("core").get("lang")
        i18n.lang_setter = lambda lang: storage.for_plugin("core").set("lang", lang)
    if result.missing_roles:
        recovery.mount(kernel)
    home.pid_path.write_text(str(os.getpid()))
    atexit.register(_remove_pid, home, os.getpid())
    ui.run(host=os.environ.get("NGUI_HOST") or "127.0.0.1",
           port=int(os.environ.get("NGUI_PORT") or 8080),
           reload=False, show=False, title="ngui", storage_secret=home.secret())
