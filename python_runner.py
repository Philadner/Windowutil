import argparse
import importlib
import json
import os
import shlex
import sys
import traceback

from colorama import Back, Fore, Style, init

import debugutils
from state import load_selected


init(autoreset=True)
debugutils.configure(os.environ.get("WUTIL_DEBUG_MODE", "off"))


def print_error(title: str, message: str, exc: Exception | None = None, entry: dict | None = None):
    if entry:
        if entry.get("arg_names"):
            args_text = ", ".join(entry["arg_names"])
        elif isinstance(entry.get("args"), list):
            args_text = ", ".join(entry["args"])
        elif isinstance(entry.get("args"), int) and entry["args"] > 0:
            args_text = f"{entry['args']} positional argument(s)"
        else:
            args_text = "No arguments"
    else:
        args_text = "No arguments"

    mode = debugutils.current_mode()
    if mode in ("off", "lite"):
        single_line_message = " ".join(message.split())
        print(
            Back.BLUE + Style.BRIGHT + f" {title.upper()} " + Style.RESET_ALL
            + Fore.WHITE + " | "
            + Back.CYAN + Fore.BLACK + f" ERROR: {single_line_message} " + Style.RESET_ALL
        )
        print(Back.CYAN + Fore.BLACK + f" Arguments: {args_text} " + Style.RESET_ALL)
        return

    width = 70
    pad = max((width - len(title) - 2) // 2, 0)
    print()
    print(Back.BLUE + Style.BRIGHT + " " * pad + f" {title.upper()} " + " " * pad + Style.RESET_ALL)
    print()
    print(Back.CYAN + Fore.BLACK + f" Arguments: {args_text} " + Style.RESET_ALL)
    print()
    print(Back.CYAN + Fore.BLACK + " Error: " + Style.RESET_ALL)
    print(Fore.WHITE + message)
    print()

    if exc is not None:
        print(Back.MAGENTA + Fore.BLACK + " Python Traceback " + Style.RESET_ALL)
        print(Fore.WHITE + traceback.format_exc().strip())
        print()


def auto_cast(value: str):
    lower = value.lower()
    if lower in ("true", "false"):
        return lower == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def converted_args(values):
    if len(values) == 1:
        values = shlex.split(values[0], posix=False)
    return [auto_cast(value) for value in values]


def main():
    parser = argparse.ArgumentParser(description="WindowUtil v3 Python compatibility runner")
    parser.add_argument("--command", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--requires-window", choices=["true", "false"], required=True)
    parser.add_argument("--arg-names", default="[]")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    args = parsed.args
    if args and args[0] == "--":
        args = args[1:]

    root = os.environ.get("WUTIL_ROOT") or os.getcwd()
    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)

    module_name = f"extensions.{parsed.file[:-3]}"
    try:
        arg_names = json.loads(parsed.arg_names)
        if not isinstance(arg_names, list):
            arg_names = []
    except json.JSONDecodeError:
        arg_names = []
    entry = {
        "arg_names": arg_names,
        "args": len(arg_names),
    }
    try:
        module = importlib.import_module(module_name)
        extension = module.Extension()
        requires_window = parsed.requires_window == "true"
        call_args = converted_args(args)

        if requires_window:
            window = load_selected()
            if window is None:
                print("No window selected. Use 'sel <name>' first.")
                return 1
            extension.main(window, *call_args)
        else:
            extension.main(*call_args)
    except Exception as exc:
        print_error(
            "WUTIL ERROR",
            f"An error occurred in module '{parsed.command}':\n{exc}",
            exc,
            entry,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
