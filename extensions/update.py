import os
import sys
import zipfile
import tempfile
import shutil
import requests
import json
from pathlib import Path

class Extension:
    def __init__(self):
        self.name = "update"
        self.desc = "Checks for and applies updates from api.phi.me.uk"
        self.args = []

    def main(self, window=None):
        print("🔎 Checking for WindowUtil updates...")

        root_dir = Path(__file__).resolve().parent.parent
        version_file = root_dir / "version.json"
        version = "0.0.0"
        if version_file.exists():
            try:
                version = json.loads(version_file.read_text()).get("version", "0.0.0")
            except Exception:
                pass

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

        tmp_extract = Path(tempfile.mkdtemp(prefix="windowutil_update_"))
        print("📂 Extracting...")
        with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
            zip_ref.extractall(tmp_extract)

        # GitHub zips include a top-level folder like Philadner-Windowutil-<sha>
        extracted_root = next(tmp_extract.iterdir())

        print("🧰 Applying update...")
        changed, skipped = [], []

        for src_path in extracted_root.rglob("*"):
            if src_path.is_dir():
                continue

            rel_path = src_path.relative_to(extracted_root)
            dest_path = root_dir / rel_path

            # Skip self and core files (require manual restart)
            if dest_path.name in ("windowutil.py", "loader.py", "update.py"):
                skipped.append(str(rel_path))
                continue

            os.makedirs(dest_path.parent, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            changed.append(str(rel_path))

        # write new version
        (root_dir / "version.json").write_text(json.dumps({"version": latest}, indent=2))

        print("\n✅ Update complete!\n")
        if changed:
            print("🔧 Updated files:")
            for f in changed:
                print(f"  - {f}")
        if skipped:
            print("\n⚠️ Skipped core files (restart or run `windowutil update` again to finish):")
            for f in skipped:
                print(f"  - {f}")

        print(f"\n✨ Now running version {latest}")
        shutil.rmtree(tmp_extract, ignore_errors=True)
        return window
