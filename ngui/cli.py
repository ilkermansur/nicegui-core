import argparse
import os
import sys
from pathlib import Path

from ngui import KERNEL_DIR, LOCALES_DIR
from ngui.app import run, signal_app
from ngui.config import home_from_env
from ngui.i18n import I18n
from ngui.manager import Manager, ManagerError
from ngui.manifest import ManifestError
from ngui.scaffold import new_plugin

# command -> (positional args, runs sync_deps on success)
COMMANDS = {"add": (["name_or_url"], True), "remove": (["id"], False), "update": (["id"], True),
            "rollback": (["id"], True), "enable": (["id"], True), "disable": (["id"], False),
            "use": (["role", "id"], False), "link": (["id", "path"], True), "unlink": (["id"], False)}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ngui")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("list")
    sub.add_parser("self-update")
    for name, (args, _) in COMMANDS.items():
        sp = sub.add_parser(name)
        for a in args:
            sp.add_argument(a)
    new = sub.add_parser("new")
    new.add_argument("name")
    new.add_argument("--dir", default=None)
    return p


def _apply(mgr: Manager, a: argparse.Namespace):
    return getattr(mgr, a.cmd)(*(getattr(a, x) for x in COMMANDS[a.cmd][0]))


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    if a.cmd == "run":
        run()
        return 0
    home = home_from_env()
    i18n = I18n(home.load_config().default_lang)
    i18n.load("core", LOCALES_DIR)
    lang = os.environ.get("NGUI_LANG") or None

    def t(key: str, **vars) -> str:
        return i18n.t("core", key, lang=lang, **vars)

    mgr = Manager(home)
    try:
        if a.cmd == "list":
            for s in mgr.status():
                print("\t".join([s.id, s.source, "✓" if s.enabled else "–", s.role, s.commit[:7], s.problem]))
            return 0
        if a.cmd == "new":
            print(t("cli.created", path=new_plugin(a.name, Path(a.dir or Path.cwd()))))
            return 0
        if a.cmd == "self-update":
            print(t("cli.self_updated", commit=mgr.self_update(KERNEL_DIR)[:7]))
        else:
            _apply(mgr, a)
            if COMMANDS[a.cmd][1]:
                mgr.sync_deps()
            print(t("cli.done", cmd=a.cmd))
    except ManagerError as e:
        print(t(e.key, **e.vars), file=sys.stderr)
        return 1
    except FileExistsError as e:
        print(t("err.exists", path=e.args[0]), file=sys.stderr)
        return 1
    except ManifestError as e:
        print(t("err.manifest", detail=str(e)), file=sys.stderr)
        return 1
    if not signal_app(home):
        print(t("cli.not_running"))
    return 0
