import time
import debugutils
mark = debugutils.mark_time
log = debugutils.log
mark("import loader.py", important=False, source="loader")

import ast, importlib, json, os, sys, threading
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
EXT_DIR = "extensions"
MANIFEST = "manifest.json"
settings_path = Path("settings.json")
auto_update = False
manifest_update_lock = threading.RLock()
manifest_update_thread = None

if settings_path.exists():
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
        auto_update = settings.get("auto-update", False)

def _extension_metadata_from_source(path, file):
    try:
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        log(f"could not read extension metadata from {file}: {exc}", source="loader")
        return None

    extension_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Extension"
        ),
        None,
    )
    if extension_class is None:
        return None

    init = next(
        (
            node
            for node in extension_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        ),
        None,
    )
    if init is None:
        return None

    metadata = {}
    for node in init.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr in {"name", "short", "desc", "args", "requires_window", "deps"}
            ):
                try:
                    metadata[target.attr] = ast.literal_eval(node.value)
                except (TypeError, ValueError):
                    log(f"metadata field {target.attr} in {file} is not a literal", source="loader")

    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        log(f"extension {file} has no literal name; skipping", source="loader")
        return None

    arg_list = metadata.get("args", [])
    if not isinstance(arg_list, list):
        arg_list = []

    manifest_entry = {
        "name": name,
        "args": len(arg_list),
        "arg_names": arg_list,
        "short": metadata.get("short", name[:3]),
        "desc": metadata.get("desc", ""),
        "requires_window": metadata.get("requires_window", True),
        "file": file
    }
    deps = metadata.get("deps")
    if isinstance(deps, list) and deps:
        manifest_entry["deps"] = deps
    return manifest_entry


def rebuild_manifest(notify=True):
    """Auto-build manifest.json by scanning all extensions."""
    with manifest_update_lock:
        mark("rebuild manifest", source="loader")
        manifest = {}
        os.makedirs(EXT_DIR, exist_ok=True)
        log(f"scanning extension directory {EXT_DIR}", important=False, source="loader")

        for file in os.listdir(EXT_DIR):
            if not file.endswith(".py") or file in {"__init__.py", "__innit__.py"}:
                continue

            log(f"reading extension metadata from {file}", important=False, source="loader")
            path = os.path.join(EXT_DIR, file)
            metadata = _extension_metadata_from_source(path, file)
            if metadata is not None:
                name = metadata.pop("name")
                manifest[name] = metadata

        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        if notify:
            print(f"[windowutil] Auto-generated manifest with {len(manifest)} extensions.")
        log(f"manifest contains {len(manifest)} commands", source="loader")
        mark("manifest rebuilt", source="loader")
        return manifest
    

def _read_manifest_from_disk():
    manifest_path = Path(MANIFEST)
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def _split_segments(argv):
    segments = []
    current = []
    for arg in argv or []:
        if arg.endswith((",", ";")):
            current.append(arg[:-1])
            segments.append(current)
            current = []
        elif arg == "then":
            segments.append(current)
            current = []
        else:
            current.append(arg)
    if current:
        segments.append(current)
    return segments


def _manifest_resolves_requested_commands(manifest, argv):
    if not argv:
        return True

    for seg in _split_segments(argv):
        if not seg:
            continue

        i = 0
        while i < len(seg):
            token = seg[i]
            cmd_key = next(
                (name for name, val in manifest.items() if token in (name, val["short"])),
                None,
            )
            if not cmd_key:
                log(f"cached manifest could not resolve token={token}", important=False, source="loader")
                return False

            entry = manifest[cmd_key]
            args_needed = len(entry.get("arg_names", [])) if isinstance(entry.get("arg_names"), list) else entry.get("args", 0)
            i += 1 + (args_needed or 0)

    return True


def auto_update_manifest(notify=True):
    with manifest_update_lock:
        mark("start check if auto update needed", important=False, source="loader")
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
                log("settings.json could not be decoded", source="loader")
                auto_update = False

        if not auto_update:
            log("auto-update disabled; skipping manifest scan", important=False, source="loader")
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
                if notify:
                    print("⚠️ manifest.json invalid — will rebuild.")
                log("manifest.json is invalid; scheduling rebuild", source="loader")
                manifest_missing = True

        manifest_files = {v["file"] for v in manifest_data.values()} if manifest_data else set()

        # --- 4. Detect differences ---
        new_files = py_files - manifest_files
        removed_files = manifest_files - py_files
        if manifest_missing or new_files or removed_files:
            if notify:
                print("🌀 Extensions changed, rebuilding manifest...")
            log(f"manifest rebuild triggered missing={manifest_missing} new={sorted(new_files)} removed={sorted(removed_files)}", source="loader")
            rebuild_manifest(notify=notify)
            if notify:
                print("✅ Manifest rebuilt.")
        mark("end check if auto update needed", important=False, source="loader")


def _start_background_manifest_refresh():
    global manifest_update_thread
    if manifest_update_thread is not None and manifest_update_thread.is_alive():
        log("background manifest refresh already running", important=False, source="loader")
        return

    log("starting background manifest refresh", important=False, source="loader")
    manifest_update_thread = threading.Thread(
        target=auto_update_manifest,
        kwargs={"notify": False},
        daemon=True,
        name="windowutil-manifest-refresh",
    )
    manifest_update_thread.start()

def load_manifest(argv=None):
    mark("load manifest", important=False, source="loader")
    manifest = _read_manifest_from_disk()

    if manifest is None:
        log("manifest missing or invalid; rebuilding synchronously", source="loader")
        return rebuild_manifest()

    if auto_update:
        if _manifest_resolves_requested_commands(manifest, argv):
            _start_background_manifest_refresh()
        else:
            log("requested command not fully covered by cached manifest; refreshing synchronously", source="loader")
            auto_update_manifest()
            manifest = _read_manifest_from_disk() or rebuild_manifest()

    log("manifest loaded from disk", important=False, source="loader")
    return manifest
    

def import_command(entry):
    mark(f"import command {entry['file']}", important=False, source="loader")
    """Dynamically import a command's file and return its class instance."""
    module_name = f"{EXT_DIR}.{entry['file'][:-3]}"
    log(f"importing module {module_name}", important=False, source="loader")
    mod = importlib.import_module(module_name)
    mark(f"done importing {entry['file']}", important=False, source="loader")
    return getattr(mod, "Extension")()
