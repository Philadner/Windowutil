# extensions/centre.py
import time
import config
import debugutils
from animations import animate_to
from wutilerror import check_types
from wutildeps import windows

mark = debugutils.mark_time
log = debugutils.log


class Extension:
    def __init__(self):
        self.name = "centre"
        self.desc = "Center a window on the screen, with optional nudge or animation."
        self.args = ["widthnudge", "heightnudge", "animated"]
        self.short = "cen"
        self.deps = ["pyautogui", "pywinctl"]

    def main(self, window, widthnudge=0, heightnudge=0, animated=True):
        mark("centre start", source="centre")
        log(f"requested centre widthnudge={widthnudge} heightnudge={heightnudge} animated={animated}", important=False, source="centre")
        check_types(
            widthnudge=(widthnudge, int, True),
            heightnudge=(heightnudge, int, True),
            animated=(animated, bool, True),
        )
        if window is None:
            log("no window supplied; prompting for title", source="centre")
            title = input("Window title: ")
            matches = windows.find_by_title(title)
            if not matches:
                print("No matching window found.")
                log(f"no matching window found for title fragment={title}", source="centre")
                return
            window = matches[0]
        log(f"centering window={window.title}", source="centre")

        screen_width, screen_height = windows.screen_size()
        log(f"screen size={screen_width}x{screen_height} current size={window.width}x{window.height}", important=False, source="centre")

        target_x = (screen_width - window.width) // 2 + int(widthnudge)
        target_y = (screen_height - window.height) // 2 + int(heightnudge)

        animated_flag = str(animated).lower() in ["true", "1", "yes"]
        if config.ANIM_ENABLED and animated_flag:
            log("using animated move", source="centre")
            animate_to(window, target_x, target_y, duration=config.ANIM_DURATION, steps=config.ANIM_STEPS)
        else:
            log("using direct move", important=False, source="centre")
            window.moveTo(target_x, target_y)

        print(f"Window '{window.title}' centered at ({target_x}, {target_y}).")
        mark("centre complete", source="centre")
        return window
