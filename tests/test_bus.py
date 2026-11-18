import asyncio

from ngui.bus import Bus, Services


def test_emit_reaches_listeners_in_order():
    b, seen = Bus(), []
    b.on("x", lambda d: seen.append(("a", d))); b.on("x", lambda d: seen.append(("b", d)))
    b.emit("x", 1)
    assert seen == [("a", 1), ("b", 1)]


def test_emit_without_listeners_is_noop():
    Bus().emit("nothing")


def test_failing_listener_does_not_stop_others(caplog):
    b, seen = Bus(), []
    b.on("x", lambda d: 1 / 0); b.on("x", seen.append)
    b.emit("x", 5)
    assert seen == [5] and "ZeroDivisionError" in caplog.text


def test_off():
    b, seen = Bus(), []
    b.on("x", seen.append); b.off("x", seen.append); b.emit("x", 1)
    assert seen == []


def test_async_listener_without_loop_is_closed_and_logged(caplog):
    async def listener(d):
        pass

    b = Bus()
    b.on("x", listener)
    b.emit("x", 1)  # no NiceGUI loop running: must not raise
    assert "x" in caplog.text


def test_async_listener_is_scheduled(monkeypatch):
    scheduled = []
    monkeypatch.setattr("nicegui.background_tasks.create", lambda aw, **kw: scheduled.append(aw))

    async def listener(d):
        pass

    b = Bus()
    b.on("x", listener)
    b.emit("x", 1)
    assert len(scheduled) == 1
    asyncio.run(scheduled[0])


def test_services():
    s = Services(); assert s.get("db") is None
    s.provide("db", 42); assert s.get("db") == 42


def test_service_override_warns(caplog):
    s = Services(); s.provide("db", 1); s.provide("db", 2)
    assert s.get("db") == 2 and "db" in caplog.text
