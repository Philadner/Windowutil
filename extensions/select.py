# extensions/select.py
import pywinctl
from state import save_selected
class Extension:
    def __init__(self):
        self.name = "select"
        self.desc = "Select a window by fuzzy title match."
        self.args = ["search_term"]
        self.short = "sel"
    def main(self, search_term):
        term = search_term.lower()
        windows = pywinctl.getAllWindows()
        matches = [w for w in windows if term in w.title.lower()]

        if not matches:
            print(f"No window found containing '{search_term}'.")
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
                return None
        else:
            window = matches[0]

        print(f"Selected window: '{window.title}'")
        save_selected(window)
        return window
