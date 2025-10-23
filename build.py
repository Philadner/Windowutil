import os
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTFILE = ROOT / "update.json"
STATEFILE = ROOT / ".build_state.json"
VERSION_FILE = ROOT / "version.json"
IGNORE = {".git", ".venv", "__pycache__", "update.json", ".gitignore", ".gitattributes", "dist"}
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
print(f"✅ wrote {len(files)} file hashes to {OUTFILE}")


# --- Check wutil.py hash ---
wutil = ROOT / "wutil.py"
wutil_hash = md5_hash(wutil) if wutil.exists() else None
last_hash = None

if STATEFILE.exists():
    try:
        last_hash = json.loads(STATEFILE.read_text()).get("wutil_hash")
    except Exception:
        pass


# --- Skip build if no changes ---
if wutil_hash == last_hash:
    print("⚙️  wutil.py unchanged — skipping PyInstaller build.")
else:
    print("⚙️  Building wutil.exe with PyInstaller...")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    try:
        subprocess.run([
            "pyinstaller",
            "--onefile",
            "--distpath", str(dist),
            "--name", "wutil",
            "wutil.py"
        ], check=True)
        print(f"✅ built {dist / 'wutil.exe'}")

        # Save new hash state
        STATEFILE.write_text(json.dumps({"wutil_hash": wutil_hash}, indent=2))
    except subprocess.CalledProcessError as e:
        print("❌ PyInstaller build failed:", e)
