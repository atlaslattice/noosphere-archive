"""One-third Work budget: a transparent bounded scheduler, not real model runs."""
from .types import snapshot

CYCLE = ("WORK", "QUIET_OPTIONAL", "SOCIAL_OR_IMAGINE_OPTIONAL")


def proposed_macrocycle(n: int, request_mode: str | None = None):
    if not isinstance(n, int) or n < 0: raise ValueError("nonnegative_cycle_index_required")
    slot = CYCLE[n % 3]
    if request_mode is not None and request_mode not in {"WORK", "QUIET", "SOCIAL", "IMAGINE", "PLAY", "REST"}:
        raise ValueError("unsupported_mode")
    return {"slot": slot, "requestedMode": request_mode,
            "workBudgetFraction": "1/3", "actuallyExecuted": False,
            "requiresExplicitParticipation": request_mode in {"SOCIAL", "IMAGINE", "PLAY"},
            "readPrivateModeIntoWork": False, "authority": "NONE"}
