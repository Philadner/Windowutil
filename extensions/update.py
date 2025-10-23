import os
import sys
import zipfile
import tempfile
import shutil
import requests
import json
import hashlib
from pathlib import Path


def md5_hash(file_path: Path) -> str:
    """Return MD5 hash for a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class Extension:
    def __init__(self):
        self.name = "update"
        self.desc = "Checks for and applies incremental updates from api.phi.me.uk"
        self.args = []

    def main(self, window=None):
        if window is not None:
            print("(i) Ignoring selected window; update works globally.")
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
        try:
            resp = requests.get(f"https://api.phi.me.uk/update/windowutil?version={version}")
            data = resp.json()
        except Exception as e:
            print(f"❌ Failed to contact update server: {e}")
            return

        if data.get("upToDate"):
            print(f"✅ WindowUtil is up to date ({data.get('latestVersion')}).")
            return

        latest = data.get("latestVersion", "?")
        zip_url = data.get("download")
        print(f"⬆️  Update available: {version} → {latest}")
        print("📦 Downloading package...")

        # --- Download the release zip ---
        try:
            r = requests.get(zip_url, stream=True)
            r.raise_for_status()
            tmp_zip = Path(tempfile.gettempdir()) / "windowutil_update.zip"
            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        except Exception as e:
            print(f"❌ Failed to download update: {e}")
            return

        # --- Extract the zip ---
        tmp_extract = Path(tempfile.mkdtemp(prefix="windowutil_update_"))
        with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
            zip_ref.extractall(tmp_extract)

        # GitHub release zips include a top-level folder like Philadner-Windowutil-<sha>
        extracted_root = next(tmp_extract.iterdir())

        # --- Read remote update.json (hash map) ---
        remote_update_file = extracted_root / "update.json"
        if not remote_update_file.exists():
            print("⚠️ No update.json found in release. Falling back to full update.")
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
        changed, skipped, identical = [], [], []

        for src_path in extracted_root.rglob("*"):
            if src_path.is_dir():
                continue
            rel_path = src_path.relative_to(extracted_root)
            dest_path = root_dir / rel_path

            # skip caches and venv junk
            if (
                "__pycache__" in str(src_path)
                or src_path.suffix in (".pyc", ".pyo")
                or src_path.name.startswith(".")
                or src_path.name.endswith(".log")
            ):
                continue

            # if hash matches, skip file
            if remote_hashes and rel_path.as_posix() in remote_hashes:
                new_hash = remote_hashes[rel_path.as_posix()]
                old_hash = local_hashes.get(rel_path.as_posix())
                if old_hash == new_hash and dest_path.exists():
                    identical.append(str(rel_path))
                    continue

            # Skip self and core files (require manual restart)
            if dest_path.name in ("windowutil.py", "loader.py", "update.py"):
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

        print("\n✅ Update complete!\n")
        if changed:
            print("🔧 Updated files:")
            for f in changed:
                print(f"  - {f}")
        if identical:
            print("\n📁 Skipped identical files:")
            for f in identical:
                print(f"  - {f}")
        if skipped:
            print("\n⚠️ Skipped core files (restart or run `windowutil update` again to finish):")
            for f in skipped:
                print(f"  - {f}")

        print(f"\n✨ Now running version {latest}")
        shutil.rmtree(tmp_extract, ignore_errors=True)
        return window
