# extensions/centre.py
# from pywin32_system32 import pygetwindow as gw
import pyautogui
import pywinctl
import time
import config
from animations import animate_to


class Extension:
    def __init__(self):
        self.name = "centre"
        self.desc = "Center a window on the screen, with optional nudge or animation."
        self.args = ["widthnudge", "heightnudge", "animated"]
        self.short = "cen"

    def main(self, window, widthnudge=0, heightnudge=0, animated=True):
        if window is None:
            title = input("Window title: ")
            matches = [w for w in pywinctl.getAllWindows() if title.lower() in w.title.lower()]
            if not matches:
                print("No matching window found.")
                return
            window = matches[0]

        screen_width, screen_height = pyautogui.size()

        target_x = (screen_width - window.width) // 2 + int(widthnudge)
        target_y = (screen_height - window.height) // 2 + int(heightnudge)

        animated_flag = str(animated).lower() in ["true", "1", "yes"]
        if config.ANIM_ENABLED and animated_flag:
            animate_to(window, target_x, target_y, duration=config.ANIM_DURATION, steps=config.ANIM_STEPS)
        else:
            window.moveTo(target_x, target_y)

        print(f"Window '{window.title}' centered at ({target_x}, {target_y}).")
        return window
