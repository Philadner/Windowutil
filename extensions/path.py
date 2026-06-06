import os
import json
import debugutils
from wutilerror import check_types
mark = debugutils.mark_time
log = debugutils.log

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".wutil")
PATH_FILE = os.path.join(CONFIG_DIR, "paths.json")
REAL_CWD = os.getenv("WUTIL_REAL_CWD")
def load_paths():
    if not os.path.exists(PATH_FILE):
        log("paths.json does not exist yet", important=False, source="path")
        return {}
    try:
        with open(PATH_FILE, "r", encoding="utf-8") as f:
            log("loading alias paths from disk", important=False, source="path")
            return json.load(f)
    except:
        log("failed to load alias paths; returning empty set", source="path")
        return {}

def save_paths(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    log(f"saving {len(data)} aliases", important=False, source="path")
    with open(PATH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class Extension:
    def __init__(self):
        self.name = "path"
        self.desc = "Manage WUtil executable aliases."
        self.args = ["action", "arg1", "arg2"]
        self.short = "p"
        self.requires_window = False

    def main(self, action=None, arg1=None, arg2=None):
        mark("path start", source="path")
        log(f"path action={action} arg1={arg1} arg2={arg2}", important=False, source="path")
        check_types(
            action=(action, str, False),
            arg1=(arg1, str, True),
            arg2=(arg2, str, True)
        )

        if action == "add":
            return self._add(arg1, arg2)
        elif action == "delete":
            return self._delete(arg1)
        elif action == "list":
            return self._list()
        else:
            print("Usage:")
            print("  wutil path add <file> <alias>")
            print("  wutil path delete <alias>")
            print("  wutil path list")

    def _add(self, file, alias):
        if not file or not alias:
            print("Usage: wutil path add <file> <alias>")
            log("path add aborted because file or alias was missing", source="path")
            return

        # Convert relative → absolute, but from the user's real cwd
        file = os.path.abspath(os.path.join(REAL_CWD, file))
        log(f"resolved alias target path={file}", important=False, source="path")

        if not os.path.exists(file):
            print(f"Error: file not found: {file}")
            log(f"path add failed because target was missing: {file}", source="path")
            return

        paths = load_paths()

        if alias in paths:
            print(f"Alias '{alias}' already exists.")
            log(f"path add rejected duplicate alias={alias}", source="path")
            return

        paths[alias] = file
        save_paths(paths)
        print(f"Added alias '{alias}' → {file}")
        log(f"alias added alias={alias}", source="path")

    def _delete(self, alias):
        if not alias:
            print("Usage: wutil path delete <alias>")
            log("path delete aborted because alias was missing", source="path")
            return

        paths = load_paths()

        if alias not in paths:
            print(f"Alias '{alias}' does not exist.")
            log(f"path delete could not find alias={alias}", source="path")
            return

        removed = paths.pop(alias)
        save_paths(paths)
        print(f"Deleted alias '{alias}' (was → {removed})")
        log(f"alias deleted alias={alias}", source="path")

    def _list(self):
        paths = load_paths()

        if not paths:
            print("No aliases stored.")
            log("path list found no aliases", source="path")
            return

        for alias, path in paths.items():
            print(f"{alias:<12} → {path}")
        log(f"listed {len(paths)} aliases", source="path")
