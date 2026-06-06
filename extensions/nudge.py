# extensions/nudge.py
import time
import threading
import math
import config
import debugutils
from wutilerror import check_types
from wutildeps import deps, windows

mark = debugutils.mark_time
log = debugutils.log

class Extension:
    def __init__(self):
        self.name = "nudge"
        self.desc = "Smooth queued nudge with diagonal support."
        self.args = ["widthnudge", "heightnudge"]
        self.short = "nud"
        self.deps = ["keyboard", "pywinctl", "pywintypes"]

    def main(self, window, widthnudge=None, heightnudge=None):
        mark("nudge start", source="nudge")
        log(f"requested nudge width={widthnudge} height={heightnudge}", important=False, source="nudge")
        check_types(
            widthnudge=(widthnudge, int, True),
            heightnudge=(heightnudge, int, True),
        )
        pywintypes = deps.pywintypes
        try:
            if window is None:
                log("no window supplied; prompting for title", source="nudge")
                title = input("Window title: ")
                matches = windows.find_by_title(title)
                if not matches:
                    print("No matching window found.")
                    log(f"no matching window found for title fragment={title}", source="nudge")
                    return
                window = matches[0]
            log(f"nudging window={window.title}", source="nudge")

            # numeric one-off nudge
            if widthnudge is not None and heightnudge is not None:
                new_left = window.left + int(widthnudge)
                new_top = window.top + int(heightnudge)
                log(f"one-off move target=({new_left}, {new_top})", source="nudge")
                window.moveTo(new_left, new_top)
                print(f"Window '{window.title}' nudged to ({new_left}, {new_top}).")
                mark("nudge complete", source="nudge")
                return window

            print("Queued nudge mode (diagonal). Use arrow keys; ESC to stop.")
            nudge_amount = getattr(config, "DEFAULT_NUDGE_STRENGTH", 10)
            move_speed = getattr(config, "NUDGE_ANIM_SPEED", 0.4)
            log(f"interactive nudge amount={nudge_amount} move_speed={move_speed}", source="nudge")

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
                    log(f"animating toward ({target['x']:.1f}, {target['y']:.1f})", important=False, source="nudge")
                    window.moveTo(int(current_x + dx * move_speed),
                                  int(current_y + dy * move_speed))
                    time.sleep(0.01)

            def handle_input():
                keyboard = deps.keyboard
                while True:
                    if keyboard.is_pressed("esc"):
                        target["stop"] = True
                        print("Exiting nudge mode.")
                        log("interactive nudge stopped by esc", source="nudge")
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
                        log(f"queued target now ({target['x']:.1f}, {target['y']:.1f})", important=False, source="nudge")
                        time.sleep(0.05)

            anim_thread = threading.Thread(target=anim_loop, daemon=True)
            anim_thread.start()
            handle_input()
            anim_thread.join()

        except pywintypes.error:
            print("Window is no longer valid (likely closed).")
            log("window handle became invalid during nudge", source="nudge")
        except Exception as e:
            print(f"An error occurred: {e}")
            log(f"nudge failed: {e}", source="nudge")
        return window
