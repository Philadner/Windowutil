import pywinctl
import pywintypes
import keyboard
import time
import threading
import config
from animations import animate_to
from wutilerror import check_types

class Extension:
    def __init__(self):
        self.name = "resize"
        self.desc = "Resize windows smoothly by side, axis, or all sides equally."
        self.args = ["side", "amount"]
        self.short = "res"

    def main(self, window, side=None, amount=None):
        check_types(
            side=(side, str)
        )
        try:
            if window is None:
                title = input("Window title: ")
                matches = [w for w in pywinctl.getAllWindows() if title.lower() in w.title.lower()]
                if not matches:
                    print("No matching window found.")
                    return
                window = matches[0]

            if not side:
                print("Missing required argument: side")
                return window

            side = side.lower()
            dirs = {
                "left": ["left", "l"],
                "right": ["right", "r"],
                "top": ["top", "up", "u"],
                "bottom": ["bottom", "down", "d"],
                "all": ["all", "equal", "eq"],
                "horizontal": ["horizontal", "hor", "x"],
                "vertical": ["vertical", "ver", "vert", "y"]
            }

            direction = None
            for key, aliases in dirs.items():
                if side in aliases:
                    direction = key
                    break
            if direction is None:
                print(f"Unknown side '{side}'")
                return window

            if amount is not None:
                self._resize_once(window, direction, int(amount))
            else:
                print(f"Interactive resize mode ({direction}). Use arrow keys, ESC to exit.")
                self._interactive_resize(window, direction)

        except pywintypes.error:
            print("Window is no longer valid (likely closed).")
        except Exception as e:
            print(f"An error occurred: {e}")

        return window

    def _resize_once(self, window, direction, delta):
        # Direct one-shot resize (simple version)
        l, t, w, h = window.left, window.top, window.width, window.height

        if direction == "left":
            l -= delta
            w += delta
        elif direction == "right":
            w += delta
        elif direction == "top":
            t -= delta
            h += delta
        elif direction == "bottom":
            h += delta
        elif direction == "horizontal":
            l -= delta // 2
            w += delta
        elif direction == "vertical":
            t -= delta // 2
            h += delta
        elif direction == "all":
            l -= delta // 2
            t -= delta // 2
            w += delta
            h += delta

        animate_to(window, l, t,
                   duration=getattr(config, "RESIZE_ANIM_DURATION", 0.15),
                   steps=getattr(config, "RESIZE_ANIM_STEPS", 15))
        window.resizeTo(w, h)

    def _interactive_resize(self, window, direction):
        resize_amount = getattr(config, "DEFAULT_RESIZE_STRENGTH", 10)
        duration = getattr(config, "RESIZE_ANIM_DURATION", 0.1)
        steps = getattr(config, "RESIZE_ANIM_STEPS", 10)

        target = {
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
            "stop": False
        }

        def anim_loop():
            while not target["stop"]:
                animate_to(window, target["left"], target["top"], duration=duration, steps=steps)
                window.resizeTo(int(target["width"]), int(target["height"]))
                time.sleep(0.01)

        def handle_input():
            while True:
                if keyboard.is_pressed("esc"):
                    target["stop"] = True
                    print("Exiting resize mode.")
                    break

                l, t, w, h = target["left"], target["top"], target["width"], target["height"]

                # --- per-side behaviour ---
                if direction == "left":
                    if keyboard.is_pressed("left"):  # grow left
                        l -= resize_amount
                        w += resize_amount
                    if keyboard.is_pressed("right"):  # shrink left
                        l += resize_amount
                        w -= resize_amount

                elif direction == "right":
                    if keyboard.is_pressed("right"):  # grow right
                        w += resize_amount
                    if keyboard.is_pressed("left"):  # shrink right
                        w -= resize_amount

                elif direction in ("top",):
                    if keyboard.is_pressed("up"):  # grow upward
                        t -= resize_amount
                        h += resize_amount
                    if keyboard.is_pressed("down"):  # shrink upward
                        t += resize_amount
                        h -= resize_amount

                elif direction in ("bottom",):
                    if keyboard.is_pressed("down"):  # grow downward
                        h += resize_amount
                    if keyboard.is_pressed("up"):  # shrink downward
                        h -= resize_amount

                elif direction == "horizontal":
                    if keyboard.is_pressed("right"):  # grow both sides
                        l -= resize_amount // 2
                        w += resize_amount
                    if keyboard.is_pressed("left"):  # shrink both sides
                        l += resize_amount // 2
                        w -= resize_amount

                elif direction == "vertical":
                    if keyboard.is_pressed("down"):  # grow both vertically
                        t -= resize_amount // 2
                        h += resize_amount
                    if keyboard.is_pressed("up"):  # shrink both vertically
                        t += resize_amount // 2
                        h -= resize_amount

                elif direction == "all":
                    if keyboard.is_pressed("down") or keyboard.is_pressed("left"): #shrink all
                        l += resize_amount // 2
                        t += resize_amount // 2
                        w -= resize_amount
                        h -= resize_amount
                    if keyboard.is_pressed("up") or keyboard.is_pressed("right"): #grow all
                        l -= resize_amount // 2
                        t -= resize_amount // 2
                        w += resize_amount
                        h += resize_amount

                target.update(left=l, top=t, width=w, height=h)
                time.sleep(0.05)

        anim_thread = threading.Thread(target=anim_loop, daemon=True)
        anim_thread.start()
        handle_input()
        anim_thread.join()
