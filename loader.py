import json, importlib.util, os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
EXT_DIR = "extensions"
MANIFEST = "manifest.json"

def rebuild_manifest():
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
            manifest[ext.name] = {
                "args": len(getattr(ext, "args", [])),
                "short": ext.name[:3],
                "file": file
            }

    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[windowutil] Auto-generated manifest with {len(manifest)} extensions.")
    return manifest


def load_manifest():
    if not os.path.exists(MANIFEST) or os.path.getsize(MANIFEST) == 0:
        return rebuild_manifest()
    with open(MANIFEST) as f:
        return json.load(f)
    

def import_command(entry):
    """Dynamically import a command's file and return its class instance."""
    module_name = f"{EXT_DIR}.{entry['file'][:-3]}"
    mod = importlib.import_module(module_name)
    return getattr(mod, "Extension")()
