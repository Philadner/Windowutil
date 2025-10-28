import time

# Globals to store timing state
_start = None
_last = None
debug = False  # Set to True to enable debug timing output

def init_timer(start_time=None):
    if debug:
        """Initialize or reset the global timing reference."""
        global _start, _last
        _start = start_time or time.time()
        _last = _start
        print(f"[debugutils] Timer initialized at {_start:.4f}")

def mark_time(label="no label"):
    if debug:
        """Mark the current time since start and since last mark."""
        global _start, _last
        if _start is None:
            print("[debugutils] Timer not initialized! Call init_timer() first.")
            return
        
        now = time.time()
        total = now - _start
        since_last = now - _last
        _last = now
        
        print(f"Doing: {label} | Total: {total:.2f}s | Since last: {since_last:.2f}s")
