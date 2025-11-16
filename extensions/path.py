import os
import json
from wutilerror import check_types

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".wutil")
PATH_FILE = os.path.join(CONFIG_DIR, "paths.json")
REAL_CWD = os.getenv("WUTIL_REAL_CWD")
def load_paths():
    if not os.path.exists(PATH_FILE):
        return {}
    try:
        with open(PATH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_paths(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(PATH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class Extension:
    def __init__(self):
        self.name = "path"
        self.desc = "Manage WUtil executable aliases."
        self.args = ["action", "arg1", "arg2"]
        self.short = "p"

    def main(self, action=None, arg1=None, arg2=None):
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
            return

        # Convert relative → absolute, but from the user's real cwd
        file = os.path.abspath(os.path.join(REAL_CWD, file))

        if not os.path.exists(file):
            print(f"Error: file not found: {file}")
            return

        paths = load_paths()

        if alias in paths:
            print(f"Alias '{alias}' already exists.")
            return

        paths[alias] = file
        save_paths(paths)
        print(f"Added alias '{alias}' → {file}")

    def _delete(self, alias):
        if not alias:
            print("Usage: wutil path delete <alias>")
            return

        paths = load_paths()

        if alias not in paths:
            print(f"Alias '{alias}' does not exist.")
            return

        removed = paths.pop(alias)
        save_paths(paths)
        print(f"Deleted alias '{alias}' (was → {removed})")

    def _list(self):
        paths = load_paths()

        if not paths:
            print("No aliases stored.")
            return

        for alias, path in paths.items():
            print(f"{alias:<12} → {path}")
