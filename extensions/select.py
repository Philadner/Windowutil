# extensions/select.py
import debugutils
from state import save_selected
from wutildeps import windows
mark = debugutils.mark_time
log = debugutils.log
class Extension:
    def __init__(self):
        self.name = "select"
        self.desc = "Select a window by fuzzy title match."
        self.args = ["search_term"]
        self.short = "sel"
        self.requires_window = False
        self.deps = ["pywinctl"]
    def main(self, search_term):
        mark("select start", source="select")
        log(f"searching for window term={search_term}", source="select")
        all_windows = windows.all_windows()
        matches = windows.find_by_title(search_term)
        log(f"window candidates total={len(all_windows)} matches={len(matches)}", important=False, source="select")

        if not matches:
            print(f"No window found containing '{search_term}'.")
            log("select found no matches", source="select")
            return None

        if len(matches) > 1:
            print(f"Multiple matches for '{search_term}':")
            for i, w in enumerate(matches):
                print(f"[{i}] {w.title}")
            try:
                index = int(input("Select index: "))
                window = matches[index]
            except (ValueError, IndexError):
                print("Invalid choice.")
                log("select received invalid interactive choice", source="select")
                return None
        else:
            window = matches[0]

        print(f"Selected window: '{window.title}'")
        log(f"selected window title={window.title}", source="select")
        save_selected(window)
        mark("select complete", source="select")
        return window
