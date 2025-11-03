import colorama
from colorama import Fore, Style, Back
colorama.init(autoreset=True)
import time
import debugutils
import traceback
debugutils.init_timer(time.time())
mark = debugutils.mark_time
mark("Start windowutil.py")

from loader import load_manifest, import_command
from state import load_selected
import os
#recursion guard
if os.environ.get("WUTIL_RUNNING") == "1":
    raise SystemExit("Already running")
os.environ["WUTIL_RUNNING"] = "1"
 
def print_error(title: str, message: str, exc: Exception | None = None, providedentry: dict | None = None):
    """Pretty WUTIL error output with argument info"""
    width = 70
    pad = (width - len(title) - 2) // 2

    print()
    print(Back.BLUE + Style.BRIGHT + " " * pad + f" {title.upper()} " + " " * pad + Style.RESET_ALL)
    print()

    if providedentry:
        # Prefer explicit arg names if available
        if "arg_names" in providedentry and providedentry["arg_names"]:
            args_text = ", ".join(providedentry["arg_names"])
        elif isinstance(providedentry.get("args"), list):
            args_text = ", ".join(providedentry["args"])
        elif isinstance(providedentry.get("args"), int) and providedentry["args"] > 0:
            args_text = f"{providedentry['args']} positional argument(s)"
        else:
            args_text = "No arguments"
        
        print(Back.CYAN + Fore.BLACK + f" Arguments: {args_text} " + Style.RESET_ALL)
        print()

    
    print(Back.CYAN + Fore.BLACK + " Error: " + Style.RESET_ALL)
    print(Fore.WHITE + message)
    print()

    if exc is not None:
        tb = traceback.format_exc()
        print(Back.MAGENTA + Fore.BLACK + " Python Traceback " + Style.RESET_ALL)
        print(Fore.WHITE + tb.strip())
        print()

def convert_args(entry, cmd_args):
    expected_arg_count = (
    len(entry["arg_names"]) if "arg_names" in entry else entry.get("args", 0)
    )
    converted_args = [auto_cast(a) for a in cmd_args][:expected_arg_count]
    return converted_args

def auto_cast(value: str):
    """Convert CLI strings to basic Python types."""
    lower = value.lower()
    if lower in ("true", "false"):
        return lower == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value  # leave as string if not numeric
    
def execute_chain(argv):
    mark("Start execute_chain")
    manifest = load_manifest()
    # --- split command segments by ; or , ---
    segments = []
    current = []
    for arg in argv:
        if arg.endswith((",", ";")):
            current.append(arg[:-1])  # add without the comma
            segments.append(current)
            current = []
        elif arg == "then":
            segments.append(current)
            current = []
        else:
            current.append(arg)
    if current:
        segments.append(current)

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
            args_needed = len(entry.get("args", [])) if isinstance(entry.get("args"), list) else entry.get("args", 0)
            cmd_args = seg[i + 1 : i + 1 + args_needed]

            ext = import_command(entry)

            if cmd_key == "select":
                window = ext.main(*convert_args(entry, cmd_args))
            else:
                if cmd_key in ("update", "help", "config", "build", "install"):
                    try:
                        ext.main(*convert_args(entry, cmd_args))
                    except Exception as e:
                        print_error("WUTIL ERROR",
                                    f"An error occurred in module '{cmd_key}':\n{e}", e, entry.get("args") if isinstance(entry.get("args"), list) else [])
                else:
                    if window is None:
                        window = load_selected()
                        if window is None:
                            print("No window selected. Use 'sel <name>' first.")
                            return
                    try:
                        
                        ext.main(window, *convert_args(entry, cmd_args))
                    except Exception as e:
                        print (entry)
                        print_error("WUTIL ERROR",
                                    f"An error occurred in module '{cmd_key}':\n{e}", e, entry)
                        return window

            # ✅ advance to next command
            i += 1 + (args_needed or 0)
                    


if __name__ == "__main__":
    import sys
    execute_chain(sys.argv[1:])
    mark("Done!")
