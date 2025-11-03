from typing import Any, get_origin, get_args
from colorama import Fore, Back, Style

# Reuse your friendly type names
TYPE_NAMES = {
    "int": "number",
    "float": "decimal number",
    "str": "text",
    "bool": "true/false value",
    "list": "list of items",
    "tuple": "tuple of values",
    "dict": "dictionary",
    "set": "set of unique values",
    "NoneType": "nothing / None",
}

def type_friendly(value):
    tname = type(value).__name__
    return TYPE_NAMES.get(tname, tname)

def type_name(t):
    """Turn <class 'int'> into 'int' cleanly."""
    if hasattr(t, "__name__"):
        return t.__name__
    return str(t)

def check_types(**typed_args: Any):
    """
    Example:
        check_types(widthnudge=(value, int), heightnudge=(other, float))
    Raises ValueError if any type is wrong.
    """
    for name, (value, expected_type) in typed_args.items():
        # handle Union, Optional etc. if needed
        origin = get_origin(expected_type)
        if origin is None:
            ok = isinstance(value, expected_type)
        else:
            # for things like Union[int, str]
            ok = any(isinstance(value, t) for t in get_args(expected_type))

        if not ok:
            raise ValueError(
                f"{name} must be a {type_friendly(expected_type())}, not {type_friendly(value)}: {value!r}"
            )
