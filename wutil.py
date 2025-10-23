# wutil.py
import subprocess
import sys
from pathlib import Path

def main():
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        base_path = Path(sys.executable).parent
        root = base_path.parent
        python_exe = "python"  # always use real Python for subprocess
    else:
        # Running as plain Python script
        root = Path(__file__).resolve().parent
        python_exe = sys.executable

    windowutil_path = root / "windowutil.py"

    if not windowutil_path.exists():
        print(f"❌ windowutil.py not found at {windowutil_path}")
        sys.exit(1)

    cmd = [python_exe, str(windowutil_path), *sys.argv[1:]]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
