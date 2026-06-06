# state.py
import json, os
import debugutils
from wutildeps import windows

STATE_FILE = ".windowutil_state.json"
log = debugutils.log

def save_selected(window):
    data = {"title": window.title}
    log(f"saving selected window title={window.title}", important=False, source="state")
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def load_selected():
    if not os.path.exists(STATE_FILE):
        log("no saved window state file found", important=False, source="state")
        return None
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        title = data.get("title", "")
        log(f"loading saved window title={title}", important=False, source="state")
        matches = windows.find_by_title(title)
        log(f"saved window match count={len(matches)}", important=False, source="state")
        return matches[0] if matches else None
    except Exception:
        log("failed to load selected window state", source="state")
        return None

def clear_selected():
    if os.path.exists(STATE_FILE):
        log("clearing selected window state", important=False, source="state")
        os.remove(STATE_FILE)
