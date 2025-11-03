import json
from pathlib import Path
from colorama import Fore, Back, Style, init
from wutilerror import check_types
init(autoreset=True)

class Extension:
    def __init__(self):
        self.name = "help"
        self.desc = "Lists all available commands, or details for a specific command."
        self.args = ["command"]
        self.short = "?"

    def main(self, command=None):
        manifest_path = Path("manifest.json")
        check_types(command=(command, str))
        if not manifest_path.exists():
            print(Fore.RED + "❌ Manifest not found. Try running 'wutil install' first.")
            return

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        if command:
            # show info for a single command
            cmd = manifest.get(command)
            if not cmd:
                # try lookup by short
                cmd = next((v for k, v in manifest.items() if v.get("short") == command), None)

            if not cmd:
                print(Fore.RED + f"❌ No command named '{command}' found.")
                return

            print(Back.BLUE + Fore.WHITE + f"  {command.upper()}  " + Style.RESET_ALL)
            print(Fore.CYAN + f"Short: {cmd.get('short')}")
            print(Fore.YELLOW + f"Description: " + Style.RESET_ALL + f"{cmd.get('desc', '')}")
            args = cmd.get("arg_names", [])
            print(Fore.MAGENTA + "Arguments: " + Style.RESET_ALL + (", ".join(args) if args else "None"))
            return

        # show all commands
        print(Back.WHITE + Fore.BLACK + " 📖 WindowUtil Command Reference " + Style.RESET_ALL + "\n")
        for name, data in manifest.items():
            short = data.get("short", "")
            desc = data.get("desc", "")
            args = data.get("arg_names", [])
            args_display = ", ".join(args) if args else "None"

            print(Fore.GREEN + f"{name:<10}" + Style.RESET_ALL + f" - {Fore.CYAN}{short}{Style.RESET_ALL}")
            print(Fore.YELLOW + f"  {desc}" + Style.RESET_ALL)
            print(Fore.MAGENTA + f"  Args: {args_display}\n" + Style.RESET_ALL)
