import debugutils

log = debugutils.log
mark = debugutils.mark_time

class Extension:
    def __init__(self):
        self.name = "failure"
        self.desc = "An extension that always fails."
        self.args = []
        self.short = "fail"
    
    def main(self, window):
        mark("failure start", source="failure")
        log(f"failure extension about to explode for window={window.title}", source="failure")
        print(f"Nice window you got there! {window.title}? Let's be a horribly made extension and error.")
        number = int("Hello")  # This will raise a ValueError
