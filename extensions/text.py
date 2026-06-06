from pathlib import Path

from wutilerror import check_types
import debugutils

log = debugutils.log
mark = debugutils.mark_time


class Extension:
    def __init__(self):
        self.name = "text"
        self.desc = "An extension to output little tidbits of text that you use regularly."
        self.args = ["id"]
        self.short = "txt"
        self.requires_window = False

    def main(self, id="empty"):
        check_types(
            id=(id, str, True)
        )

        mark("text start", source="text")

        text_path = Path.home() / ".wutil" / "text" / f"{id}.txt"

        if not text_path.exists():
            print(f"Text '{id}' not found.")
            log(f"text not found. id={id}", source="text")
            return
        text = text_path.read_text(encoding="utf-8")

        print(text)

        log(f"text outputted. id={id}", source="text")