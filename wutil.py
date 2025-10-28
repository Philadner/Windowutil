# wutil.py
import subprocess
import sys
from pathlib import Path

# --- this constant will be replaced at build time ---
INSTALL_PATH = "{{INSTALL_PATH}}"  

def main():
    if getattr(sys, 'frozen', False):
        # exe is inside wutil/, so go up one folder
        exe_dir = Path(sys.executable).resolve().parent
        root = exe_dir.parent
        python_exe = str(root / ".venv" / "Scripts" / "python.exe")
    else:
        root = Path(__file__).resolve().parent
        python_exe = sys.executable

    windowutil_path = root / "windowutil.py"
    if not windowutil_path.exists():
        print(f"❌ windowutil.py not found at {windowutil_path}")
        sys.exit(1)

    cmd = [python_exe, str(windowutil_path), *sys.argv[1:]]
    subprocess.run(cmd, cwd=root)  # ✅ force correct working dir

if __name__ == "__main__":
    main()
