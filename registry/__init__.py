"""Public-only Atlas repository source registry. No network or authorization."""
from importlib import import_module

__all__ = ["validate_catalog", "lookup_public_repo", "route_public_issue", "RegistryError"]


def __getattr__(name):
    # Keep the package API without preloading the CLI before `python -m`.
    # An eager import makes runpy emit RuntimeWarning (or fail under -W error).
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".public_registry", __name__), name)
    globals()[name] = value
    return value
