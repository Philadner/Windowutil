import time

_start = None
_last = None
debug = False
mode = "off"

_MODE_SETTINGS = {
    "off": {"show_marks": False, "show_logs": False, "verbose_marks": False, "verbose_logs": False},
    "lite": {"show_marks": True, "show_logs": True, "verbose_marks": False, "verbose_logs": False},
    "normal": {"show_marks": True, "show_logs": True, "verbose_marks": False, "verbose_logs": False},
    "speed": {"show_marks": True, "show_logs": False, "verbose_marks": True, "verbose_logs": False},
    "hard": {"show_marks": True, "show_logs": True, "verbose_marks": True, "verbose_logs": True},
}


def configure(debug_mode):
    global debug, mode
    mode = debug_mode if debug_mode in _MODE_SETTINGS else "off"
    debug = mode != "off"


def is_enabled():
    return mode != "off"


def current_mode():
    return mode


def _settings():
    return _MODE_SETTINGS.get(mode, _MODE_SETTINGS["off"])


def _should_show(kind, important):
    settings = _settings()
    if kind == "mark":
        return settings["show_marks"] and (important or settings["verbose_marks"])
    if kind == "log":
        return settings["show_logs"] and (important or settings["verbose_logs"])
    return False


def _elapsed(now):
    if _start is None:
        return 0.0, 0.0
    return now - _start, now - _last


def _level_tag(important):
    return "main" if important else "detail"


def _source_tag(source):
    return source if source else "core"


def init_timer(start_time=None):
    global _start, _last
    _start = start_time or time.time()
    _last = _start
    if _should_show("log", True):
        print(f"[debug:{mode}] [init] [core] timer started at {_start:.4f}")


def mark_time(label="no label", important=True, source=None):
    global _start, _last
    now = time.time()
    if _start is None:
        _start = now
        _last = now
    total, since_last = _elapsed(now)
    _last = now
    if _should_show("mark", important):
        print(
            f"[debug:{mode}] [mark:{_level_tag(important)}] "
            f"[{_source_tag(source)}] {label} | total {total:.3f}s | +{since_last:.3f}s"
        )


def log(message, important=True, source=None):
    if not _should_show("log", important):
        return
    now = time.time()
    if _start is None:
        total = 0.0
    else:
        total = now - _start
    print(
        f"[debug:{mode}] [log:{_level_tag(important)}] "
        f"[{_source_tag(source)}] +{total:.3f}s {message}"
    )
