"""Sentinel: tool output is data, not commands."""
__version__ = "1.0.0"


def __getattr__(name):  # lazy: importing the package must not load any model
    if name in ("Sentinel", "Guard"):
        if name == "Sentinel":
            from .pipeline import Sentinel
            return Sentinel
        from .guard import Guard
        return Guard
    raise AttributeError(name)
