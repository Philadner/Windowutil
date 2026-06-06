from functools import cached_property

import debugutils


log = debugutils.log


class SharedDeps:
    def _load(self, module_name):
        log(f"loading shared dependency {module_name}", important=False, source="wutildeps")
        return __import__(module_name)

    @cached_property
    def keyboard(self):
        return self._load("keyboard")

    @cached_property
    def psutil(self):
        return self._load("psutil")

    @cached_property
    def pyautogui(self):
        return self._load("pyautogui")

    @cached_property
    def pywinctl(self):
        return self._load("pywinctl")

    @cached_property
    def pywintypes(self):
        return self._load("pywintypes")

    @cached_property
    def requests(self):
        return self._load("requests")


class WindowsDeps:
    def __init__(self, deps):
        self._deps = deps

    def all_windows(self):
        return self._deps.pywinctl.getAllWindows()

    def find_by_title(self, title_fragment):
        term = title_fragment.lower()
        return [w for w in self.all_windows() if term in w.title.lower()]

    def screen_size(self):
        return self._deps.pyautogui.size()


deps = SharedDeps()
windows = WindowsDeps(deps)
