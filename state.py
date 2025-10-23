# state.py
import json, os, pywinctl

STATE_FILE = ".windowutil_state.json"

def save_selected(window):
    data = {"title": window.title}
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def load_selected():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        title = data.get("title", "")
        matches = [w for w in pywinctl.getAllWindows() if title.lower() in w.title.lower()]
        return matches[0] if matches else None
    except Exception:
        return None

def clear_selected():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
