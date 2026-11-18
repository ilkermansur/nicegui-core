from nicegui import ui

from ngui.context import Kernel


def mount(kernel: Kernel) -> None:
    def t(key: str, **vars) -> str:
        return kernel.i18n.t("core", key, lang=kernel.i18n.default_lang, **vars)  # no storage

    @ui.page("/{_path:path}")
    def page(_path: str = "") -> None:
        result = kernel.result
        ui.label(t("recovery.title")).classes("text-h5")
        for role in result.missing_roles:
            ui.label(t("recovery.missing_role", role=role))
        if result.broken:
            ui.label(t("recovery.broken")).classes("text-h6")
            for pid, why in sorted(result.broken.items()):
                ui.label(f"{pid}: {why}")
        ui.label(t("recovery.fix_hint"))
        for cmd in ("ngui list", "ngui use <rol> <id>", "ngui add <ad>"):
            ui.code(cmd).classes("w-full")
