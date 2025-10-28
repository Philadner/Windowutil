import psutil

class Extension:
    def __init__(self):
        self.name = "terminate"
        self.short = "term"
        self.desc = "Terminate (kill) the currently selected window's process."
        self.args = []

    def main(self, window=None):
        if window is None:
            print("⚠️ No window selected.")
            return

        pid = None

        # ✅ pywinctl provides getPID()
        if hasattr(window, "getPID"):
            try:
                pid = window.getPID()
            except Exception as e:
                print(f"⚠️ getPID() failed: {e}")

        if not pid:
            print("❌ Could not resolve process ID for this window.")
            return

        try:
            proc = psutil.Process(pid)
            print(f"💀 Terminating {window.title} (PID {pid})...")
            proc.terminate()
        except Exception as e:
            print(f"❌ Failed to terminate process {pid}: {e}")
