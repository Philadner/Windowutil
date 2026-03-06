class Extension:
    def __init__(self):
        self.name = "failure"
        self.desc = "An extension that always fails."
        self.args = []
        self.short = "fail"
    
    def main(self, window):
        print(f"Nice window you got there! {window.title}? Let's be a horribly made extension and error.")
        number = int("Hello")  # This will raise a ValueError