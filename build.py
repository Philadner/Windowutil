import os
import hashlib
import json
from pathlib import Path

# --- CONFIG ---
ROOT = Path(__file__).resolve().parent
OUTFILE = ROOT / "update.json"
VERSION_FILE = ROOT / "version.json"
IGNORE = {
    ".git",
    ".venv",
    "__pycache__",
    "update.json",
    ".gitignore",
    ".gitattributes",
    "dist",
}

# --- LOAD VERSION ---
if VERSION_FILE.exists():
    version = json.loads(VERSION_FILE.read_text()).get("version", "0.0.0")
else:
    version = "0.0.0"

# --- HASHING FUNCTION ---
def md5_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# --- WALK PROJECT ---
files = {}
for path in ROOT.rglob("*"):
    if path.is_file():
        rel = path.relative_to(ROOT).as_posix()
        if any(part in IGNORE for part in path.parts):
            continue
        files[rel] = md5_hash(path)

# --- WRITE OUTPUT ---
data = {
    "version": version,
    "files": files,
}

OUTFILE.write_text(json.dumps(data, indent=2))
print(f"✅ Wrote {len(files)} file hashes to {OUTFILE}")
