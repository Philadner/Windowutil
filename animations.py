import time
import config
def easeInOutQuad(t):
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

def animate_to(window, target_x, target_y, duration=0.4, steps=100 * config.ANIM_DURATION + 100):
    if config.RETURN_DURATION:
        print (config.ANIM_DURATION)
    start_x, start_y = window.left, window.top
    for i in range(steps + 1):
        t = i / steps
        ease = easeInOutQuad(t)
        new_x = int(start_x + (target_x - start_x) * ease)
        new_y = int(start_y + (target_y - start_y) * ease)
        window.moveTo(new_x, new_y)
        time.sleep(duration / steps)