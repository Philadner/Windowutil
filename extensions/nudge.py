# extensions/nudge.py
import pywinctl
import pywintypes
import keyboard
import time
import threading
import math
import config
from wutilerror import check_types

class Extension:
    def __init__(self):
        self.name = "nudge"
        self.desc = "Smooth queued nudge with diagonal support."
        self.args = ["widthnudge", "heightnudge"]
        self.short = "nud"

    def main(self, window, widthnudge=None, heightnudge=None):
        if widthnudge is not None or heightnudge is not None:
            check_types(
                widthnudge=(widthnudge, int),
                heightnudge=(heightnudge, int),
            )
        try:
            if window is None:
                title = input("Window title: ")
                matches = [w for w in pywinctl.getAllWindows() if title.lower() in w.title.lower()]
                if not matches:
                    print("No matching window found.")
                    return
                window = matches[0]

            # numeric one-off nudge
            if widthnudge is not None and heightnudge is not None:
                new_left = window.left + int(widthnudge)
                new_top = window.top + int(heightnudge)
                window.moveTo(new_left, new_top)
                print(f"Window '{window.title}' nudged to ({new_left}, {new_top}).")
                return window

            print("Queued nudge mode (diagonal). Use arrow keys; ESC to stop.")
            nudge_amount = getattr(config, "DEFAULT_NUDGE_STRENGTH", 10)
            move_speed = getattr(config, "NUDGE_ANIM_SPEED", 0.4)

            target = {"x": window.left, "y": window.top, "stop": False}

            def anim_loop():
                while not target["stop"]:
                    current_x, current_y = window.left, window.top
                    dx = target["x"] - current_x
                    dy = target["y"] - current_y

                    # Skip if small
                    if abs(dx) < 1 and abs(dy) < 1:
                        time.sleep(0.01)
                        continue

                    # Move smoothly toward target
                    window.moveTo(int(current_x + dx * move_speed),
                                  int(current_y + dy * move_speed))
                    time.sleep(0.01)

            def handle_input():
                while True:
                    if keyboard.is_pressed("esc"):
                        target["stop"] = True
                        print("Exiting nudge mode.")
                        break

                    dx = int(keyboard.is_pressed("right")) - int(keyboard.is_pressed("left"))
                    dy = int(keyboard.is_pressed("down")) - int(keyboard.is_pressed("up"))

                    if dx or dy:
                        # normalize diagonal so it moves same speed in all directions
                        mag = math.sqrt(dx * dx + dy * dy)
                        dx /= mag
                        dy /= mag
                        target["x"] += dx * nudge_amount
                        target["y"] += dy * nudge_amount
                        time.sleep(0.05)

            anim_thread = threading.Thread(target=anim_loop, daemon=True)
            anim_thread.start()
            handle_input()
            anim_thread.join()

        except pywintypes.error:
            print("Window is no longer valid (likely closed).")
        except Exception as e:
            print(f"An error occurred: {e}")
        return window
