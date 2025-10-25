import os
import json
import pathlib
from loader import rebuild_manifest

class Extension:
    def __init__(self):
        self.name = "install"
        self.desc = "When you drag new extensions in, run this to rebuild the manifest"
        self.args = ["auto-toggle"]
        self.short = "inst"

    def main(self, auto_toggle=None):
        # --- Rebuild manifest ---
        manifest = pathlib.Path("manifest.json")
        if manifest.exists():
            os.remove(manifest)
        rebuild_manifest()
        print("✅ Manifest rebuilt.")

        # --- Handle settings toggle or explicit on/off ---
        if auto_toggle is not None:
            settings_path = pathlib.Path("settings.json")

            # Load or initialize settings
            if settings_path.exists():
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except json.JSONDecodeError:
                    print("⚠️ settings.json was corrupt — recreating.")
                    settings = {}
            else:
                settings = {}

            # Normalize argument
            arg = str(auto_toggle).strip().lower()
            enable_keywords = {"enable", "-enable", "e", "-e", "on", "-on", "true"}
            disable_keywords = {"disable", "-disable", "d", "-d", "off", "-off", "false"}

            # Determine new state
            if arg in enable_keywords:
                new_state = True
            elif arg in disable_keywords:
                new_state = False
            else:
                # Toggle if no explicit value
                new_state = not settings.get("auto-update", False)

            # Write new state
            settings["auto-update"] = new_state
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)

            state_str = "enabled" if new_state else "disabled"
            print(f"🔁 Auto-update has been {state_str}.")
