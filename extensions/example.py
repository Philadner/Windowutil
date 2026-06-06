from wutilerror import check_types
import os
import debugutils
log = debugutils.log
mark = debugutils.mark_time
class Extension:
    def __init__(self):
        self.name = "example"
        self.desc = "An example extention to help show code structure."
        self.args = ["text"]
        self.short = "eg"

    def main(self, window, text="Hello, World!"):
        mark("example start", source="example")
    #stuff provided by wutil:
        #because extebnsions are run in a subprocess, we can get the real cwd fron env vars
        cwd = os.getenv("WUTIL_REAL_CWD")
        window #the current selected window.
        #use wutilerror to check types
        # variable, type, optional?
        check_types(
            text=(text, str, True)
        )
        log(f"example window={window.title} text={text}", source="example")
        
        print(f"""
Example extension executed with text: {text}
Current working directory: {cwd}
the selected window is: {window.title}
""")
