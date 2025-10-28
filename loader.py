import time
import debugutils
mark = debugutils.mark_time
mark("import loader.py")

import json, importlib.util, os, sys
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
EXT_DIR = "extensions"
MANIFEST = "manifest.json"
settings_path = Path("settings.json")
auto_update = False

if settings_path.exists():
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
        auto_update = settings.get("auto-update", False)

def rebuild_manifest():
    mark("rebuild manifest")
    """Auto-build manifest.json by scanning all extensions."""
    manifest = {}
    os.makedirs(EXT_DIR, exist_ok=True)

    for file in os.listdir(EXT_DIR):
        if not file.endswith(".py") or file == "__init__.py":
            continue

        path = os.path.join(EXT_DIR, file)
        spec = importlib.util.spec_from_file_location(file[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if hasattr(mod, "Extension"):
            ext = mod.Extension()

            # Fallbacks for optional attributes
            short = getattr(ext, "short", ext.name[:3])
            desc = getattr(ext, "desc", "")
            arg_list = getattr(ext, "args", [])
            arg_count = len(arg_list)

            manifest[ext.name] = {
                "args": arg_count,
                "arg_names": arg_list,
                "short": short,
                "desc": desc,
                "file": file
            }

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[windowutil] Auto-generated manifest with {len(manifest)} extensions.")
    mark("manifest rebuilt")
    return manifest
    

def auto_update_manifest():
    mark("start check if auto update needed")
    settings_path = Path("settings.json")
    manifest_path = Path("manifest.json")
    extensions_dir = Path("extensions")

    # --- 1. Check if auto-update is enabled ---
    auto_update = False
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                auto_update = settings.get("auto-update", False)
        except json.JSONDecodeError:
            print("⚠️ settings.json invalid — ignoring auto-update.")
            auto_update = False

    if not auto_update:
        return  # skip silently

    # --- 2. Collect extension filenames ---
    py_files = {
        f.name
        for f in extensions_dir.glob("*.py")
        if f.name not in {"__innit__.py", "__pycache__"}
    }

    # --- 3. Load manifest ---
    manifest_missing = not manifest_path.exists()
    manifest_data = {}
    if not manifest_missing:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ manifest.json invalid — will rebuild.")
            manifest_missing = True

    manifest_files = {v["file"] for v in manifest_data.values()} if manifest_data else set()

    # --- 4. Detect differences ---
    new_files = py_files - manifest_files
    removed_files = manifest_files - py_files
    if manifest_missing or new_files or removed_files:
        print("🌀 Extensions changed, rebuilding manifest...")
        rebuild_manifest()
        print("✅ Manifest rebuilt.")
    mark("end check if auto update needed")

def load_manifest():
    mark("load manifest")
    if auto_update:
        auto_update_manifest()
    """Load manifest.json, rebuilding if missing or empty."""
    if not os.path.exists(MANIFEST) or os.path.getsize(MANIFEST) == 0:
        return rebuild_manifest()
    with open(MANIFEST) as f:
        return json.load(f)
    mark("end load manifest")
    

def import_command(entry):
    mark(f"import command {entry}")
    """Dynamically import a command's file and return its class instance."""
    module_name = f"{EXT_DIR}.{entry['file'][:-3]}"
    mod = importlib.import_module(module_name)
    mark(f"done importing {entry}")
    return getattr(mod, "Extension")()
