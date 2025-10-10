"""FlowManager Ryu application package."""

__all__ = ["FlowManager"]


def __getattr__(name):
    if name == "FlowManager":
        from .flowmanager import FlowManager

        return FlowManager
    raise AttributeError(f"module 'flowmanager' has no attribute {name!r}")
