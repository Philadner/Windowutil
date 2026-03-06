import json
import os
import re
import hashlib
import uuid
from datetime import datetime
from colorama import Fore, Style, init as colorama_init
from wutilerror import check_types


def _base_dir():
    home = os.path.expanduser("~")
    return os.path.join(home, ".wutil", "notes")


def _index_path():
    return os.path.join(_base_dir(), "index.json")


def _notes_dir():
    return os.path.join(_base_dir(), "notes")


def _ensure_dirs():
    os.makedirs(_notes_dir(), exist_ok=True)


def _note_filename(note_id):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", note_id).strip("_")
    digest = hashlib.sha1(note_id.encode("utf-8")).hexdigest()[:8]
    if not safe:
        safe = "note"
    return f"note_{safe}_{digest}.json"


def _load_index():
    _ensure_dirs()
    path = _index_path()
    if not os.path.exists(path):
        return {"notes": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "notes" in data and isinstance(data["notes"], dict):
            return data
    except Exception:
        pass
    return {"notes": {}}


def _save_index(index):
    _ensure_dirs()
    with open(_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def _note_path(filename):
    return os.path.join(_notes_dir(), filename)


def _load_note_file(filename):
    path = _note_path(filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _save_note_file(filename, note):
    _ensure_dirs()
    with open(_note_path(filename), "w", encoding="utf-8") as f:
        json.dump(note, f, indent=2)


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _preview(text, length=100):
    compact = " ".join((text or "").split())
    if len(compact) <= length:
        return compact
    return compact[: max(0, length - 3)] + "..."


def _migrate_legacy_if_present():
    legacy_path = os.path.join(os.getenv("WUTIL_REAL_CWD") or os.getcwd(), ".windowutil_notes.json")
    if not os.path.exists(legacy_path):
        return

    try:
        with open(legacy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    if isinstance(data, dict) and "notes" in data and isinstance(data["notes"], dict):
        legacy_notes = data["notes"]
    elif isinstance(data, dict):
        legacy_notes = data
    else:
        return

    index = _load_index()
    for note_id, note in legacy_notes.items():
        if note_id in index["notes"]:
            continue
        filename = _note_filename(note_id)
        note_obj = {
            "id": note_id,
            "text": note.get("text", ""),
            "created_at": note.get("created_at") or _now_iso(),
            "labels": note.get("labels", []) or [],
            "links": note.get("links", []) or [],
        }
        _save_note_file(filename, note_obj)
        index["notes"][note_id] = {"file": filename}

    _save_index(index)


def _init_ui():
    colorama_init(autoreset=True)


def _header(text):
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")


def _prompt(text, default=None, allow_blank=False):
    while True:
        if default:
            raw = input(f"{Fore.YELLOW}{text}{Style.RESET_ALL} [{default}]: ").strip()
            if not raw:
                raw = default
        else:
            raw = input(f"{Fore.YELLOW}{text}{Style.RESET_ALL}: ").strip()
        if not raw and not allow_blank:
            print(f"{Fore.RED}Value required.{Style.RESET_ALL}")
            continue
        return raw


def _prompt_multiline(text):
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Finish with a single '.' on its own line.{Style.RESET_ALL}")
    lines = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).rstrip("\n")


def _generate_id():
    return uuid.uuid4().hex[:8]


def _needs_interactive_text(value):
    if not value:
        return True
    if value.startswith("'") and not value.endswith("'"):
        return True
    return False


def _strip_outer_quotes(value):
    if not isinstance(value, str):
        return value
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


class Extension:
    def __init__(self):
        self.name = "note"
        self.desc = "Create and manage simple linked notes."
        self.args = ["action", "arg1", "arg2"]
        self.short = "nt"

    def main(self, action=None, arg1=None, arg2=None):
        check_types(
            action=(action, str, False),
            arg1=(arg1, str, True),
            arg2=(arg2, str, True),
        )

        _migrate_legacy_if_present()

        if not action:
            return self._usage()

        action = action.lower()
        if action == "add":
            return self._add(arg1, arg2)
        if action == "link":
            return self._link(arg1, arg2)
        if action == "unlink":
            return self._unlink(arg1, arg2)
        if action in ("delete", "del"):
            return self._delete(arg1)
        if action == "list":
            return self._list()
        if action in ("inspect", "ins"):
            return self._inspect(arg1)
        if action == "search":
            return self._search(arg1)
        if action == "read":
            return self._read(arg1)
        if action in ("label", "lab"):
            return self._label(arg1, arg2)
        if action in ("unlabel", "unlab", "tagdel", "tagrm"):
            return self._unlabel(arg1, arg2)

        self._usage()

    def _usage(self):
        print("Usage:")
        print('  wutil note add "note id" "Note here"')
        print('  wutil note link "note id 1" "note id 2"')
        print('  wutil note unlink "note id 1" "note id 2"')
        print('  wutil note delete|del "note id"')
        print("  wutil note list")
        print('  wutil note inspect|ins "note id"')
        print('  wutil note search "text"')
        print('  wutil note read "note id"')
        print('  wutil note label|lab "note id" "label"')
        print('  wutil note unlabel|unlab "note id" "label"')
        print("Tip: use double quotes for multi-word text, or run without args for interactive mode.")

    def _index_note(self, note_id):
        index = _load_index()
        entry = index["notes"].get(note_id)
        if not entry:
            return None, index
        return entry, index

    def _load_note(self, note_id):
        entry, index = self._index_note(note_id)
        if not entry:
            return None, index
        note = _load_note_file(entry.get("file", ""))
        return note, index

    def _save_note(self, note_id, note, index):
        entry = index["notes"].get(note_id)
        if not entry:
            filename = _note_filename(note_id)
            index["notes"][note_id] = {"file": filename}
        else:
            filename = entry.get("file") or _note_filename(note_id)
            index["notes"][note_id] = {"file": filename}
        _save_note_file(filename, note)
        _save_index(index)

    def _add(self, note_id, text):
        if not note_id or _needs_interactive_text(text):
            return self._add_ui(note_id)
        note_id = _strip_outer_quotes(note_id).strip()
        text = _strip_outer_quotes(text)

        index = _load_index()
        if note_id in index["notes"]:
            print(f"Note '{note_id}' already exists.")
            return

        note = {
            "id": note_id,
            "text": text,
            "created_at": _now_iso(),
            "labels": [],
            "links": [],
        }
        self._save_note(note_id, note, index)
        print(f"Added note '{note_id}'.")

    def _add_ui(self, note_id=None):
        _init_ui()
        _header("Create Note")
        if note_id:
            print(f"{Fore.WHITE}Using ID: {note_id}{Style.RESET_ALL}")
        else:
            suggested = _generate_id()
            note_id = _prompt("Note ID (blank = auto)", default=suggested, allow_blank=True)
            if not note_id:
                note_id = suggested

        index = _load_index()
        if note_id in index["notes"]:
            print(f"{Fore.RED}Note '{note_id}' already exists.{Style.RESET_ALL}")
            return

        text = _prompt_multiline("Enter note content")
        if not text.strip():
            print(f"{Fore.RED}Note content required.{Style.RESET_ALL}")
            return

        note = {
            "id": note_id,
            "text": text,
            "created_at": _now_iso(),
            "labels": [],
            "links": [],
        }
        self._save_note(note_id, note, index)
        print(f"{Fore.GREEN}Added note '{note_id}'.{Style.RESET_ALL}")

    def _link(self, id1, id2):
        if not id1 or not id2:
            return self._link_ui()
        id1 = _strip_outer_quotes(id1).strip()
        id2 = _strip_outer_quotes(id2).strip()
        if id1 == id2:
            print("Cannot link a note to itself.")
            return

        note1, index = self._load_note(id1)
        note2, index = self._load_note(id2)
        if not note1 or not note2:
            print("Both notes must exist to link them.")
            return

        for note, other_id in ((note1, id2), (note2, id1)):
            links = note.setdefault("links", [])
            if other_id not in links:
                links.append(other_id)

        self._save_note(id1, note1, index)
        self._save_note(id2, note2, index)
        print(f"Linked '{id1}' <-> '{id2}'.")

    def _link_ui(self):
        _init_ui()
        _header("Link Notes")
        id1 = _prompt("First note ID")
        id2 = _prompt("Second note ID")
        return self._link(id1, id2)

    def _unlink(self, id1, id2):
        if not id1 or not id2:
            return self._unlink_ui()
        id1 = _strip_outer_quotes(id1).strip()
        id2 = _strip_outer_quotes(id2).strip()
        if id1 == id2:
            print("Cannot unlink a note from itself.")
            return

        note1, index = self._load_note(id1)
        note2, index = self._load_note(id2)
        if not note1 or not note2:
            print("Both notes must exist to unlink them.")
            return

        def _remove_link(note, other_id):
            links = note.get("links", [])
            if other_id in links:
                note["links"] = [l for l in links if l != other_id]
                return True
            return False

        changed = False
        changed |= _remove_link(note1, id2)
        changed |= _remove_link(note2, id1)

        if not changed:
            print("Notes were not linked.")
            return

        self._save_note(id1, note1, index)
        self._save_note(id2, note2, index)
        print(f"Unlinked '{id1}' <-> '{id2}'.")

    def _unlink_ui(self):
        _init_ui()
        _header("Unlink Notes")
        id1 = _prompt("First note ID")
        id2 = _prompt("Second note ID")
        return self._unlink(id1, id2)

    def _delete(self, note_id):
        if not note_id:
            return self._delete_ui()
        note_id = _strip_outer_quotes(note_id).strip()

        index = _load_index()
        entry = index["notes"].get(note_id)
        if not entry:
            print(f"Note '{note_id}' does not exist.")
            return

        filename = entry.get("file")
        if filename:
            path = _note_path(filename)
            if os.path.exists(path):
                os.remove(path)

        index["notes"].pop(note_id, None)
        _save_index(index)

        for other_id in list(index["notes"].keys()):
            note = _load_note_file(index["notes"][other_id].get("file", ""))
            if not note:
                continue
            links = note.get("links", [])
            if note_id in links:
                note["links"] = [l for l in links if l != note_id]
                _save_note_file(index["notes"][other_id]["file"], note)

        print(f"Deleted note '{note_id}'.")

    def _delete_ui(self):
        _init_ui()
        _header("Delete Note")
        note_id = _prompt("Note ID")
        confirm = _prompt("Type DELETE to confirm", allow_blank=True)
        if confirm != "DELETE":
            print(f"{Fore.YELLOW}Cancelled.{Style.RESET_ALL}")
            return
        return self._delete(note_id)

    def _list(self):
        index = _load_index()
        if not index["notes"]:
            print("No notes stored.")
            return

        for note_id in sorted(index["notes"].keys()):
            note = _load_note_file(index["notes"][note_id].get("file", ""))
            if not note:
                continue
            labels = note.get("labels", [])
            label_text = f" [{', '.join(labels)}]" if labels else ""
            print(f"{note_id}: {_preview(note.get('text', ''), 60)}{label_text}")

    def _inspect(self, note_id):
        if not note_id:
            return self._inspect_ui()
        note_id = _strip_outer_quotes(note_id).strip()

        note, _ = self._load_note(note_id)
        if not note:
            print(f"Note '{note_id}' not found.")
            return

        created = note.get("created_at", "unknown")
        labels = note.get("labels", [])
        links = note.get("links", [])
        print(f"ID: {note_id}")
        print(f"Created: {created}")
        print(f"Preview: {_preview(note.get('text', ''), 120)}")
        print(f"Labels: {', '.join(labels) if labels else '(none)'}")
        print(f"Links: {', '.join(links) if links else '(none)'}")

    def _inspect_ui(self):
        _init_ui()
        _header("Inspect Note")
        note_id = _prompt("Note ID")
        return self._inspect(note_id)

    def _search(self, query):
        if _needs_interactive_text(query):
            return self._search_ui()
        query = _strip_outer_quotes(query)

        index = _load_index()
        q = query.lower()
        matches = []
        for note_id, entry in index["notes"].items():
            note = _load_note_file(entry.get("file", ""))
            if not note:
                continue
            text = (note.get("text", "") or "").lower()
            labels = [l.lower() for l in note.get("labels", [])]
            if q in text or any(q in l for l in labels):
                matches.append(note_id)

        if not matches:
            print("No matches found.")
            return

        for note_id in sorted(matches):
            note = _load_note_file(index["notes"][note_id].get("file", ""))
            if not note:
                continue
            print(f"{note_id}: {_preview(note.get('text', ''), 60)}")

    def _search_ui(self):
        _init_ui()
        _header("Search Notes")
        query = _prompt("Search text", allow_blank=True)
        if not query:
            print(f"{Fore.YELLOW}Cancelled.{Style.RESET_ALL}")
            return
        return self._search(query)

    def _read(self, note_id):
        if not note_id:
            print('Usage: wutil note read "note id"')
            return
        note_id = _strip_outer_quotes(note_id).strip()

        note, _ = self._load_note(note_id)
        if not note:
            print(f"Note '{note_id}' not found.")
            return

        print(note.get("text", ""))

    def _label(self, note_id, label):
        if not note_id or _needs_interactive_text(label):
            return self._label_ui()
        note_id = _strip_outer_quotes(note_id).strip()
        label = _strip_outer_quotes(label)

        label = label.strip()
        if not label:
            print("Label cannot be empty.")
            return

        note, index = self._load_note(note_id)
        if not note:
            print(f"Note '{note_id}' not found.")
            return

        labels = note.setdefault("labels", [])
        if label.lower() in (l.lower() for l in labels):
            print(f"Label '{label}' already exists on '{note_id}'.")
            return

        labels.append(label)
        self._save_note(note_id, note, index)
        print(f"Added label '{label}' to '{note_id}'.")

    def _label_ui(self):
        _init_ui()
        _header("Label Note")
        note_id = _prompt("Note ID")
        label = _prompt("Label")
        return self._label(note_id, label)

    def _unlabel(self, note_id, label):
        if not note_id or _needs_interactive_text(label):
            return self._unlabel_ui()
        note_id = _strip_outer_quotes(note_id).strip()
        label = _strip_outer_quotes(label)

        note, index = self._load_note(note_id)
        if not note:
            print(f"Note '{note_id}' not found.")
            return

        labels = note.get("labels", [])
        target = None
        for existing in labels:
            if existing.lower() == label.lower():
                target = existing
                break

        if not target:
            print(f"Label '{label}' not found on '{note_id}'.")
            return

        note["labels"] = [l for l in labels if l != target]
        self._save_note(note_id, note, index)
        print(f"Removed label '{target}' from '{note_id}'.")

    def _unlabel_ui(self):
        _init_ui()
        _header("Remove Label")
        note_id = _prompt("Note ID")
        label = _prompt("Label")
        return self._unlabel(note_id, label)
