from wutilerror import check_types
import os
import json
import subprocess
import sys
import debugutils

mark = debugutils.mark_time
log = debugutils.log

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".wutil")
PATH_FILE = os.path.join(CONFIG_DIR, "paths.json")

def load_paths():
    if not os.path.exists(PATH_FILE):
        log("run could not find paths.json", important=False, source="run")
        return {}
    try:
        with open(PATH_FILE, "r", encoding="utf-8") as f:
            log("run loaded aliases from disk", important=False, source="run")
            return json.load(f)
    except:
        log("run failed to decode aliases file", source="run")
        return {}

class Extension:
    def __init__(self):
        self.name = "run"
        self.desc = "Run an alias created with wutil path."
        self.args = ["alias", "args"]
        self.short = "r"
        self.requires_window = False

    def main(self, alias=None, args=None):
        mark("run start", source="run")
        log(f"run requested alias={alias} args={args}", important=False, source="run")
        check_types(
            alias=(alias, str, False),
            args=(args, str, True)
        )

        paths = load_paths()

        if alias not in paths:
            print(f"Alias '{alias}' not found.")
            log(f"run failed because alias={alias} was missing", source="run")
            return

        exe = paths[alias]

        if not os.path.exists(exe):
            print(f"Stored file no longer exists: {exe}")
            log(f"run failed because target path was missing: {exe}", source="run")
            return

        exe_dir = os.path.dirname(exe)  # <-- THIS FIXES EVERYTHING

        arg_list = args.split(" ") if args else []

        # Allow stored paths to be Python scripts as well as native executables
        if exe.lower().endswith(".py"):
            cmd = [sys.executable, exe] + arg_list
        else:
            cmd = [exe] + arg_list

        try:
            log(f"launching command={cmd} cwd={exe_dir}", source="run")
            subprocess.run(
                cmd,
                cwd=exe_dir,   # <-- force real working directory
            )
        except Exception as e:
            print(f"Failed to run alias: {e}")
            log(f"run failed for alias={alias}: {e}", source="run")
