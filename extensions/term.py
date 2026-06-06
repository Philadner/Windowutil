import debugutils
from wutildeps import deps

mark = debugutils.mark_time
log = debugutils.log

class Extension:
    def __init__(self):
        self.name = "terminate"
        self.short = "term"
        self.desc = "Terminate (kill) the currently selected window's process."
        self.args = []
        self.deps = ["psutil"]

    def main(self, window=None):
        mark("terminate start", source="term")
        psutil = deps.psutil
        if window is None:
            print("⚠️ No window selected.")
            log("terminate aborted because no window was selected", source="term")
            return

        pid = None
        log(f"attempting terminate for window={window.title}", source="term")

        # ✅ pywinctl provides getPID()
        if hasattr(window, "getPID"):
            try:
                pid = window.getPID()
            except Exception as e:
                print(f"⚠️ getPID() failed: {e}")
                log(f"window.getPID failed: {e}", source="term")

        if not pid:
            print("❌ Could not resolve process ID for this window.")
            log("terminate aborted because pid could not be resolved", source="term")
            return

        try:
            proc = psutil.Process(pid)
            print(f"💀 Terminating {window.title} (PID {pid})...")
            log(f"terminating pid={pid}", source="term")
            proc.terminate()
        except Exception as e:
            print(f"❌ Failed to terminate process {pid}: {e}")
            log(f"terminate failed for pid={pid}: {e}", source="term")
