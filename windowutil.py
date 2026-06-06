import debugutils
import sys
import time

RAW_ARGS = sys.argv[1:]
DEBUG_FLAGS = {
    "--debug-lite": "lite",
    "--debug-speed": "speed",
    "--debug": "normal",
    "--debug-hard": "hard",
}
selected_debug_mode = next((DEBUG_FLAGS[arg] for arg in RAW_ARGS if arg in DEBUG_FLAGS), "off")
CLI_ARGS = [arg for arg in RAW_ARGS if arg not in DEBUG_FLAGS]

debugutils.configure(selected_debug_mode)

debugutils.init_timer(time.time())
mark = debugutils.mark_time
log = debugutils.log
mark("Start windowutil.py", source="windowutil")
log(f"debug mode set to {debugutils.current_mode()}", source="windowutil")

mark("imports", important=False, source="windowutil")
#mark ("colorama")
import colorama
from colorama import Fore, Style, Back
#mark ("traceback")
import traceback
#mark ("loader")
from loader import load_manifest, import_command
#mark ("state")
from state import load_selected
#mark ("os")
import os

colorama.init(autoreset=True)
mark("imports done and colorama initialized", important=False, source="windowutil")

#recursion guard
mark("recursion guard check", important=False, source="windowutil")
if os.environ.get("WUTIL_RUNNING") == "1":
    raise SystemExit("Already running")
os.environ["WUTIL_RUNNING"] = "1"
mark("Process function definitions", important=False, source="windowutil")
def print_error(title: str, message: str, exc: Exception | None = None, providedentry: dict | None = None):
    """Pretty WUTIL error output with argument info"""
    mode = debugutils.current_mode()
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

    else:
        args_text = "No arguments"

    if mode in ("off", "lite"):
        single_line_message = " ".join(message.split())
        print(Back.BLUE + Style.BRIGHT + f" {title.upper()} " + Style.RESET_ALL + Fore.WHITE + f" | " + Back.CYAN + Fore.BLACK + f" ERROR: {single_line_message} " + Style.RESET_ALL)
        print(Back.CYAN + Fore.BLACK + f" Arguments: {args_text} " + Style.RESET_ALL)
        return

    width = 70
    pad = (width - len(title) - 2) // 2

    print()
    print(Back.BLUE + Style.BRIGHT + " " * pad + f" {title.upper()} " + " " * pad + Style.RESET_ALL)
    print()
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

import shlex

def convert_args(entry, cmd_args):
    # If cmd_args is already a list, join it
    if isinstance(cmd_args, list):
        cmd_args = " ".join(cmd_args)

    # NOW it's safe to split
    args = shlex.split(cmd_args, posix=False)

    expected_arg_count = (
        len(entry.get("arg_names", [])) 
        if "arg_names" in entry 
        else entry.get("args", 0)
    )

    converted_args = [auto_cast(a) for a in args][:expected_arg_count]

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
    mark("Start execute_chain", source="windowutil")
    log(f"received argv={argv}", important=False, source="windowutil")
    manifest = load_manifest(argv)
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
        log(f"processing segment={seg}", important=False, source="windowutil")
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
                log(f"unknown command token={token}", source="windowutil")
                i += 1
                continue

            entry = manifest[cmd_key]
            log(f"resolved command={cmd_key} entry={entry}", important=False, source="windowutil")
            args_needed = len(entry.get("args", [])) if isinstance(entry.get("args"), list) else entry.get("args", 0)
            cmd_args = seg[i + 1 : i + 1 + args_needed]
            log(f"command args raw={cmd_args}", important=False, source="windowutil")

            ext = import_command(entry)
            requires_window = getattr(ext, "requires_window", entry.get("requires_window", True))
            log(f"command requires_window={requires_window}", important=False, source="windowutil")

            if cmd_key == "select":
                mark("run select", source="windowutil")
                window = ext.main(*convert_args(entry, cmd_args))
            else:
                if not requires_window:
                    try:
                        mark(f"run global command {cmd_key}", source="windowutil")
                        ext.main(*convert_args(entry, cmd_args))
                    except Exception as e:
                        log(f"global command {cmd_key} failed: {e}", source="windowutil")
                        print_error("WUTIL ERROR",
                                    f"An error occurred in module '{cmd_key}':\n{e}", e, entry.get("args") if isinstance(entry.get("args"), list) else [])
                else:
                    if window is None:
                        log(f"no window cached for {cmd_key}, loading selected window", important=False, source="windowutil")
                        window = load_selected()
                        if window is None:
                            print("No window selected. Use 'sel <name>' first.")
                            log(f"command {cmd_key} aborted because no window was selected", source="windowutil")
                            return
                    try:
                        mark(f"run window command {cmd_key}", source="windowutil")
                        ext.main(window, *convert_args(entry, cmd_args))
                    except Exception as e:
                        log(f"window command {cmd_key} failed: {e}", source="windowutil")
                        if debugutils.current_mode() not in ("off", "lite"):
                            print(entry)
                        print_error("WUTIL ERROR",
                                    f"An error occurred in module '{cmd_key}':\n{e}", e, entry)
                        return window

            # ✅ advance to next command
            i += 1 + (args_needed or 0)

mark("Finished processing functions", important=False, source="windowutil")    


if __name__ == "__main__":
    execute_chain(CLI_ARGS)
    mark("Done!", source="windowutil")
