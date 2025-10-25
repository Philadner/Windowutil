import subprocess
import sys
from pathlib import Path

def main():
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        root = exe_dir.parent
        python_exe = root / ".venv" / "Scripts" / "python.exe"
    else:
        root = Path(__file__).resolve().parent.parent
        python_exe = sys.executable

    windowutil_path = root / "windowutil.py"
    if not windowutil_path.exists():
        sys.exit(f"❌ windowutil.py not found at {windowutil_path}")

    subprocess.run([python_exe, str(windowutil_path), *sys.argv[1:]], cwd=root)

if __name__ == "__main__":
    main()
