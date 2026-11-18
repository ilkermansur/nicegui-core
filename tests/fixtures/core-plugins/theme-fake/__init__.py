from nicegui import ui


class _Theme:
    mode = "auto"

    def set_mode(self, mode):
        self.mode = mode

    def card(self, title=None, actions=None):
        card = ui.card()
        with card:
            if title:
                ui.label(title)
            if actions:
                actions()
        return card

    def kpi(self, label, value, icon=None, tone="neutral"):
        with ui.card() as card:
            ui.label(label)
            ui.label(str(value))
        return card

    def page_header(self, title, description=None):
        ui.label(title)
        if description:
            ui.label(description)


def setup(ctx):
    return _Theme()
