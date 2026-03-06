import keyboard
import time
from colorama import Fore, Style, init as colorama_init


class Tools:
    def subscript_maker():
        colorama_init(autoreset=True)
        subs = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'}
        state = {
            'await': False,
            'paused': False,
            'handlers': [],
            'start': time.time(),
            'toggles': 0,
            'subs_made': 0,
            'digits_typed': 0,
            'await_cancels': 0,
            'spinner_idx': 0,
        }
        spinner = ["|", "/", "-", "\\"]
        moods = ["Zippy", "Cosmic", "Wobbly", "Snug", "Chaotic", "Zen"]

        def render_status():
            elapsed = int(time.time() - state['start'])
            mm, ss = divmod(elapsed, 60)
            status = "PAUSED" if state['paused'] else "ACTIVE"
            status_color = Fore.YELLOW if state['paused'] else Fore.GREEN
            mood = moods[(state['subs_made'] + state['toggles']) % len(moods)]
            sparkle = (state['subs_made'] * 7 + state['digits_typed'] * 3) % 101
            spin = spinner[state['spinner_idx'] % len(spinner)]
            state['spinner_idx'] += 1
            line = (
                f"{Fore.CYAN}Subscript Maker{Style.RESET_ALL} "
                f"{status_color}{status}{Style.RESET_ALL} {spin}  "
                f"{Fore.MAGENTA}subs:{state['subs_made']}{Style.RESET_ALL} "
                f"{Fore.BLUE}digits:{state['digits_typed']}{Style.RESET_ALL} "
                f"{Fore.RED}cancels:{state['await_cancels']}{Style.RESET_ALL} "
                f"{Fore.YELLOW}toggles:{state['toggles']}{Style.RESET_ALL} "
                f"{Fore.GREEN}mood:{mood}{Style.RESET_ALL} "
                f"{Fore.WHITE}sparkle:{sparkle}%{Style.RESET_ALL} "
                f"{Fore.CYAN}time:{mm:02d}:{ss:02d}{Style.RESET_ALL}"
            )
            print("\r" + line.ljust(140), end="", flush=True)

        def attach_handlers():
            # Attach handlers. suppress=True stops the original key from being sent so we control output.
            state['handlers'].append(keyboard.on_press_key('`', on_backtick, suppress=True))
            for d in subs:
                state['handlers'].append(
                    keyboard.on_press_key(d, lambda e, digit=d: on_digit(e, digit), suppress=True)
                )
            # Hook other keys to cancel awaiting when needed
            state['handlers'].append(keyboard.hook(on_other))

        def detach_handlers():
            while state['handlers']:
                keyboard.unhook(state['handlers'].pop())

        def on_toggle_pause(e):
            # Toggle pause state for the hook logic
            state['paused'] = not state['paused']
            state['await'] = False
            state['toggles'] += 1
            if state['paused']:
                detach_handlers()
            else:
                attach_handlers()
            render_status()

        def on_backtick(e):
            # Suppress the backtick and activate awaiting state
            state['await'] = True
            render_status()

        def on_digit(e, d):
            if state['await']:
                # replace next digit with subscript
                keyboard.write(subs[d])
                state['await'] = False
                state['subs_made'] += 1
            else:
                # if not awaiting, emit the digit as normal (we suppressed original)
                keyboard.write(d)
                state['digits_typed'] += 1
            render_status()

        def on_other(e):
            # if awaiting and any non-digit/non-backtick key is pressed, cancel awaiting
            if state['await'] and e.name not in ('`',) and e.name not in tuple(subs.keys()):
                state['await'] = False
                state['await_cancels'] += 1
                render_status()

        # Pause toggle stays active even when handlers are detached.
        keyboard.on_press_key('#', on_toggle_pause, suppress=True)
        attach_handlers()

        print("Subscript maker active. Press ESC to stop.")
        render_status()
        keyboard.wait('esc')
        print()


class Extension:
    def __init__(self):
        self.name = "keyboardutil"
        self.desc = "Utility functions for keyboard input handling."
        self.args = ["tool"]
        self.short = "kbu"

    def main(self, tool):
        print(f"Keyboard utility tool: {tool}")
        # Tool: SubscriptMaker
        if tool.lower() in ("subscript", "subscriptmaker", "subscrpt", "sub"):
            Tools.subscript_maker()
