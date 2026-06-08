import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTFILE = ROOT / "update.json"
STATEFILE = ROOT / ".build_state.json"
VERSION_FILE = ROOT / "version.json"
IGNORE = {".git", ".venv", ".wutil", "__pycache__", "update.json", ".gitignore", ".gitattributes", "dist"}
VERSION = "0.0.0"

# --- Hashing helper ---
def md5_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# --- Read version ---
if VERSION_FILE.exists():
    VERSION = json.loads(VERSION_FILE.read_text()).get("version", VERSION)


# --- Walk project and hash files ---
files = {}
for path in ROOT.rglob("*"):
    if path.is_file() and not any(part in IGNORE for part in path.parts):
        files[path.relative_to(ROOT).as_posix()] = md5_hash(path)

data = {"version": VERSION, "files": files}
OUTFILE.write_text(json.dumps(data, indent=2))
print(f"[ok] wrote {len(files)} file hashes to {OUTFILE}")


# --- Check Go entrypoint hash ---
go_sources = sorted(ROOT.rglob("*.go"))
go_inputs = go_sources + [path for path in [ROOT / "go.mod", ROOT / "go.sum"] if path.exists()]
go_hash_parts = [md5_hash(path) for path in go_inputs]
wutil_hash = hashlib.md5("".join(go_hash_parts).encode("utf-8")).hexdigest() if go_hash_parts else None
last_hash = None

if STATEFILE.exists():
    try:
        last_hash = json.loads(STATEFILE.read_text()).get("wutil_hash")
    except Exception:
        pass


# --- Skip build if no changes ---
if wutil_hash == last_hash:
    print("[build] Go entrypoint unchanged - skipping go build.")
else:
    print("[build] Building wutil.exe with Go...")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    try:
        subprocess.run([
            "go",
            "build",
            "-o", str(dist / "wutil.exe"),
            "./cmd/wutil",
        ], check=True)
        print(f"[ok] built {dist / 'wutil.exe'}")
    
        # Save new hash state
        STATEFILE.write_text(json.dumps({"wutil_hash": wutil_hash}, indent=2))
    except subprocess.CalledProcessError as e:
        print("[error] Go build failed:", e)
