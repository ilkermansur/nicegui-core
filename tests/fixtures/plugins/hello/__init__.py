from nicegui import ui


def setup(ctx):
    ctx.services.provide("hello.ping", lambda: "pong")

    @ctx.role("layout").page("/hello", ctx.t("title"))
    def page():
        ui.label(ctx.t("greet"))
