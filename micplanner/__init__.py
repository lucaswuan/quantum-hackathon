"""IM-free wireless mic planner: plain-English frequency planning through QAOA."""

from .engine import build_instance, check_plan, brute_force

__all__ = ["build_instance", "check_plan", "brute_force", "plan_mics"]


def __getattr__(name):
    # plan_mics pulls in Qiskit, so import it only when asked for.
    if name == "plan_mics":
        from .api import plan_mics
        return plan_mics
    raise AttributeError(name)
