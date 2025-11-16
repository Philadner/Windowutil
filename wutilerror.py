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
        check_types(maybe_val=(value, int, True))  # third element True marks value optional (None allowed)
        check_types(either=(value, Optional[int]))  # typing.Optional / Union still handled normally

    Raises ValueError if any type is wrong.
    """
    for name, spec in typed_args.items():
        # spec expected to be (value, expected_type) or (value, expected_type, optional_bool)
        if not (isinstance(spec, (list, tuple)) and len(spec) >= 2):
            raise ValueError(f"Invalid spec for {name}; expected (value, expected_type[, optional_bool])")

        value, expected_type = spec[0], spec[1]
        optional_flag = bool(spec[2]) if len(spec) >= 3 and isinstance(spec[2], bool) else False

        # helper to determine if value matches a (possibly typing) type
        def matches(val, typ) -> bool:
            if typ is Any:
                return True
            origin = get_origin(typ)
            if origin is None:
                # typ should be a plain class/type
                try:
                    return isinstance(val, typ)
                except TypeError:
                    # typ might be something like typing.AnyStr that isn't directly instantiable/usable with isinstance
                    return False
            # handle Union/Optional etc.
            return any(matches(val, t) for t in get_args(typ))

        # allow None if optional_flag set or expected_type explicitly includes None
        origin = get_origin(expected_type)
        args = get_args(expected_type) if origin is not None else ()
        allows_none = optional_flag or any(a is type(None) for a in args) or expected_type is type(None)

        ok = False
        if value is None:
            ok = allows_none
        else:
            ok = matches(value, expected_type)

        if not ok:
            # build a readable expected-type description
            def expected_desc(typ):
                origin = get_origin(typ)
                if origin is None:
                    return TYPE_NAMES.get(type_name(typ), type_name(typ))
                parts = [TYPE_NAMES.get(type_name(t), type_name(t)) for t in get_args(typ)]
                return " or ".join(parts)

            desc = expected_desc(expected_type)
            if optional_flag and "None" not in desc and not any("None" in p for p in (args if args else [])):
                desc = f"{desc} or None"

            raise ValueError(f"{name} must be {desc}, not {type_friendly(value)}: {value!r}")
