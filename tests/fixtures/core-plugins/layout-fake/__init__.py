from nicegui import ui


class _Layout:
    def __init__(self):
        self.slots = {}

    def page(self, path, title, icon=None, permission=None):
        def decorator(fn):
            @ui.page(path)
            def wrapper():
                ui.label("LAYOUT-FAKE")
                fn()

            return fn

        return decorator

    def add(self, slot, builder):
        if slot in ("header", "footer", "sidebar"):
            self.slots.setdefault(slot, []).append(builder)


def setup(ctx):
    return _Layout()
