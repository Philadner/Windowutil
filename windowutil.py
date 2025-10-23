from loader import load_manifest, import_command
from state import load_selected
def execute_chain(argv):
    manifest = load_manifest()

    # --- NEW: split command segments by ; or , ---
    #  e.g. ['sel', 'zen', 'nudge;', 'centre']
    #  becomes [['sel','zen','nudge'], ['centre']]
    segments = []
    current = []
    for arg in argv:
        # handle multiple delimiters in one token, e.g. "nudge;"
        if ';' in arg or ',' in arg or 'then' in arg:
            cleaned = arg.rstrip(';,"then"')
            if cleaned:
                current.append(cleaned)
            segments.append(current)
            current = []
        else:
            current.append(arg)
    if current:
        segments.append(current)

    # --- execute each segment separately ---
    window = None
    for seg in segments:
        if not seg:
            continue

        i = 0
        while i < len(seg):
            token = seg[i]
            cmd_key = next(
                (name for name, val in manifest.items()
                 if token in (name, val["short"])),
                None,
            )
            if not cmd_key:
                print(f"Unknown command: {token}")
                i += 1
                continue

            entry = manifest[cmd_key]
            args_needed = entry.get("args", 0)
            cmd_args = seg[i + 1 : i + 1 + args_needed]

            ext = import_command(entry)
            if cmd_key == "select":
                window = ext.main(*cmd_args)
            else:
                if window is None and entry not in ("update", "help", "config", "build"):
                    window = load_selected()
                    if window is None:
                        print("No window selected. Use 'sel <name>' first.")
                        return
                window = ext.main(window, *cmd_args)

            i += 1 + args_needed

    return window

if __name__ == "__main__":
    import sys
    execute_chain(sys.argv[1:])
