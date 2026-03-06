from wutilerror import check_types
import code
import math
from fractions import Fraction
import textwrap

class Extension:
    def __init__(self):
        self.name = "mathenv"
        self.desc = "Live maths environment with helpers."
        self.args = []
        self.short = "mth"

    def main(self):
        # ---------------------
        # Built-in maths helpers
        # ---------------------
        
        # solve linear equations: ax + b = c
        def solve_linear(a, b, c):
            return (c - b) / a
        
        # simplify fractions
        def frac(x, y=None):
            if y is None:
                return Fraction(x)
            return Fraction(x, y)

        # round to dp
        def rd(x, dp=2):
            return round(x, dp)

        # distance formula
        def dist(x1, y1, x2, y2):
            return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # pythagoras
        def hyp(a, b):
            return math.sqrt(a*a + b*b)

        # angle in degrees
        def deg(rad):
            return rad * 180 / math.pi

        # angle in radians
        def rad(deg_val):
            return deg_val * math.pi / 180

        # simple expand: (a+b)^2, (a-b)^2
        def expand_square(a, b, sign="+"):
            if sign == "+":
                return a*a + 2*a*b + b*b
            return a*a - 2*a*b + b*b

        def percent_reduction(original, new):
            """
            Returns the percentage decrease from 'original' to 'new'.
            Example: percent_reduction(100, 75) → 25.0
            """
            if original == 0:
                return None  # can't reduce from zero
            return ((original - new) / original) * 100

        # a little object whose repr prints help
        class MathHelpObject:
            def __repr__(self):
                return textwrap.dedent("""
                =======================
                 WUTIL MATH HELP PANEL
                =======================

                Preloaded functions:

                  frac(x, y)     → Fraction
                  rd(x, dp)      → Round
                  hyp(a, b)      → Pythagoras
                  dist(x1,y1,x2,y2) → Distance
                  deg(rad)       → Radians → Degrees
                  rad(deg)       → Degrees → Radians
                  solve_linear(a, b, c)
                      solves ax + b = c

                  expand_square(a,b,"+" or "-")
                  percent_reduction(original, new)

                Examples:
                  >>> frac(3,4)
                  >>> rd(5/3, 3)
                  >>> hyp(3,4)
                  >>> solve_linear(3, 2, 11)
                  >>> expand_square(2, 5, "+")
                  >>> deg(math.pi/3)

                Type:
                    mathhelp
                to show this panel again.
                """)
            
            def __call__(self):
                print(self.__repr__())

        mathhelp = MathHelpObject()

        # ---------------------
        # Build env for REPL
        # ---------------------
        env = {
            # maths objects
            "math": math,
            "Fraction": Fraction,

            # helpers
            "frac": frac,
            "rd": rd,
            "hyp": hyp,
            "dist": dist,
            "deg": deg,
            "rad": rad,
            "expand_square": expand_square,
            "solve_linear": solve_linear,
            "percent_reduction": percent_reduction,
            # help panel
            "mathhelp": mathhelp,
        }

        banner = """
========================================
       WUTIL MATH LIVE ENV READY
========================================
Type:
   mathhelp
to see available commands.

No window required.
========================================
"""

        code.InteractiveConsole(env).interact(banner)
