import time
import debugutils
mark = debugutils.mark_time
mark("import update.py")
import os
import sys
import zipfile
import tempfile
import shutil
import base64
import json
import hashlib
import subprocess
import time
from pathlib import Path
from wutildeps import deps
log = debugutils.log
UPDATE_URL = "https://hub.phi.me.uk/update/windowutil"


def md5_hash(file_path: Path) -> str:
    """Return MD5 hash for a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def launch_update_worker(skipped_files, extracted_root, root_dir):
    """Spawn a background worker to finish replacing locked files."""
    worker_path = root_dir / "_update_worker.py"

    # Build argument list for the worker (list of relative file paths)
    args_json = json.dumps(skipped_files)
    code = f"""
import os, time, json, shutil, sys
from pathlib import Path

root_dir = Path(r"{root_dir}")
src_root = Path(r"{extracted_root}")
skipped = json.loads(r'''{args_json}''')

print("🕐 Waiting for WindowUtil to close...")
time.sleep(1.0)

for i in range(50):  # try for ~5s
    try:
        for rel in skipped:
            src = src_root / rel
            dest = root_dir / rel
            if not src.exists():
                continue
            os.makedirs(dest.parent, exist_ok=True)
            shutil.copy2(src, dest)
        print("✅ Core files replaced successfully.")
        break
    except PermissionError:
        time.sleep(0.1)
else:
    print("⚠️ Could not replace some files; still locked.")

# cleanup temp directory
try:
    shutil.rmtree(src_root)
except Exception:
    pass

# remove self
try:
    os.remove(__file__)
except Exception:
    pass

# relaunch wutil if exists
exe = root_dir / "dist" / "wutil.exe"
if exe.exists():
    try:
        print("🚀 Relaunching WindowUtil...")
        os.startfile(exe)
    except Exception:
        pass
"""

    worker_path.write_text(code, encoding="utf-8")
    subprocess.Popen([sys.executable, str(worker_path)], creationflags=subprocess.CREATE_NO_WINDOW)
    print("🧩 Finishing update in background...\n")
    time.sleep(0.5)
    sys.exit(0)


def _safe_relative_path(rel_path):
    path = Path(rel_path)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _write_patch_files(files, extracted_root):
    written = []
    for item in files:
        rel_path = _safe_relative_path(item.get("path", ""))
        if rel_path is None:
            continue

        if item.get("encoding") != "base64":
            continue

        dest = extracted_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(item.get("content", "")))
        written.append(rel_path.as_posix())
    return written


def _remove_deleted_files(root_dir, removed_files):
    removed = []
    for rel in removed_files or []:
        rel_path = _safe_relative_path(rel)
        if rel_path is None:
            continue
        target = root_dir / rel_path
        if target.exists() and target.is_file():
            target.unlink()
            removed.append(rel_path.as_posix())
    return removed


class Extension:
    def __init__(self):
        self.name = "update"
        self.desc = "Checks for and applies incremental updates from hub.phi.me.uk"
        self.args = []
        self.short = "updt"
        self.requires_window = False
        self.deps = ["requests"]

    def main(self):
        mark("start update extension", source="update")
        requests = deps.requests
        log("checking for updates", source="update")
        print("🔎 Checking for WindowUtil updates...")

        root_dir = Path(__file__).resolve().parent.parent
        version_file = root_dir / "version.json"
        version = "0.0.0"
        if version_file.exists():
            try:
                version = json.loads(version_file.read_text()).get("version", "0.0.0")
            except Exception:
                pass

        # --- Fetch release info from Cloudflare Worker ---
        mark("start update fetch", important=False, source="update")
        try:
            local_update_file = root_dir / "update.json"
            if local_update_file.exists():
                try:
                    local_manifest = json.loads(local_update_file.read_text(encoding="utf-8"))
                except Exception:
                    local_manifest = {"version": version, "files": {}}
            else:
                local_manifest = {"version": version, "files": {}}

            resp = requests.post(
                f"{UPDATE_URL}?version={version}",
                json=local_manifest,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message")
        except Exception as e:
            print(f"❌ Failed to contact update server: {e}")
            log(f"update server request failed: {e}", source="update")
            return
        
        if data.get("upToDate"):
            print(message)
            return
        
        latest = data.get("latestVersion", "?")
        patch_files = data.get("files")
        zip_url = data.get("download")
        log(f"update available current={version} latest={latest}", source="update")
        print(message)
        mark("end update fetch", important=False, source="update")

        tmp_extract = Path(tempfile.mkdtemp(prefix="windowutil_update_"))
        extracted_root = tmp_extract / "patch"
        extracted_root.mkdir(parents=True, exist_ok=True)

        if isinstance(patch_files, list):
            print("📦 Downloading changed files...")
            _write_patch_files(patch_files, extracted_root)
            update_manifest = data.get("updateManifest") or {}
            remote_hashes = update_manifest.get("files", {})
        else:
            print("📦 Downloading package...")
            try:
                r = requests.get(zip_url, stream=True)
                r.raise_for_status()
                tmp_zip = Path(tempfile.gettempdir()) / "windowutil_update.zip"
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
            except Exception as e:
                print(f"❌ Failed to download update: {e}")
                log(f"update download failed: {e}", source="update")
                return

            with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
                zip_ref.extractall(tmp_extract)

            extracted_root = next(tmp_extract.iterdir())

            # --- Read remote update.json (hash map) ---
            remote_update_file = extracted_root / "update.json"
            if not remote_update_file.exists():
                print("⚠️ No update.json found in release. Falling back to full update.")
                log("downloaded update had no update.json", source="update")
                remote_hashes = None
            else:
                remote_hashes = json.loads(remote_update_file.read_text())["files"]

        # --- Compare with local hashes (if available) ---
        local_hashes = {}
        local_update_file = root_dir / "update.json"
        if local_update_file.exists():
            try:
                local_hashes = json.loads(local_update_file.read_text())["files"]
            except Exception:
                pass

        print("🧰 Applying update...")
        log("starting incremental file apply", source="update")
        changed, skipped, identical = [], [], []

        for src_path in extracted_root.rglob("*"):
            if src_path.is_dir():
                continue
            rel_path = src_path.relative_to(extracted_root)
            dest_path = root_dir / rel_path

            if (
                "__pycache__" in str(src_path)
                or src_path.suffix in (".pyc", ".pyo")
                or src_path.name.startswith(".")
                or src_path.name.endswith(".log")
            ):
                continue

            if remote_hashes and rel_path.as_posix() in remote_hashes:
                new_hash = remote_hashes[rel_path.as_posix()]
                old_hash = local_hashes.get(rel_path.as_posix())
                if old_hash == new_hash and dest_path.exists():
                    identical.append(str(rel_path))
                    continue

            # skip locked core files
            if dest_path.name.lower() in (
                "update.py", 
                "wutil.exe", 
                "_update_worker.py"
                ):
                skipped.append(str(rel_path))
                continue

            os.makedirs(dest_path.parent, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            changed.append(str(rel_path))

        # update local update.json + version
        if remote_hashes:
            (root_dir / "update.json").write_text(json.dumps({
                "version": latest,
                "files": remote_hashes
            }, indent=2))

        (root_dir / "version.json").write_text(json.dumps({"version": latest}, indent=2))
        removed = _remove_deleted_files(root_dir, data.get("removed", []))

        print("\n✅ Update complete!\n")
        log(f"update finished changed={len(changed)} identical={len(identical)} skipped={len(skipped)}", source="update")
        if changed:
            print("🔧 Updated files:")
            for f in changed:
                print(f"  - {f}")
        if identical:
            print("\n📁 Skipped identical files:")
            for f in identical:
                print(f"  - {f}")
        if skipped:
            print("\n⚠️ Skipped core files (will be replaced after WindowUtil closes):")
            for f in skipped:
                print(f"  - {f}")
            launch_update_worker(skipped, extracted_root, root_dir)
            return
        if removed:
            print("\n🗑️ Removed old files:")
            for f in removed:
                print(f"  - {f}")

        print(f"\n✨ Now running version {latest}")
        shutil.rmtree(tmp_extract, ignore_errors=True)
