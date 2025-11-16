from wutilerror import check_types
import os
import json
import subprocess

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".wutil")
PATH_FILE = os.path.join(CONFIG_DIR, "paths.json")

def load_paths():
    if not os.path.exists(PATH_FILE):
        return {}
    try:
        with open(PATH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

class Extension:
    def __init__(self):
        self.name = "run"
        self.desc = "Run an alias created with wutil path."
        self.args = ["alias", "args"]
        self.short = "r"

    def main(self, alias=None, args=None):
        check_types(
            alias=(alias, str, False),
            args=(args, str, True)
        )

        paths = load_paths()

        if alias not in paths:
            print(f"Alias '{alias}' not found.")
            return

        exe = paths[alias]

        if not os.path.exists(exe):
            print(f"Stored file no longer exists: {exe}")
            return

        exe_dir = os.path.dirname(exe)  # <-- THIS FIXES EVERYTHING

        arg_list = args.split(" ") if args else []

        try:
            subprocess.run(
                [exe] + arg_list,
                cwd=exe_dir,   # <-- force real working directory
            )
        except Exception as e:
            print(f"Failed to run alias: {e}")
