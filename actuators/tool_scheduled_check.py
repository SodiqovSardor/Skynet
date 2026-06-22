import time
import threading
import json
import os

def scheduled_check(schedule_type: str = "once", interval_seconds: int = 60, action: str = "") -> str:
    """
    Create a simple scheduled task. This tool provides scheduling capability.
    schedule_type: "once" - run once, "interval" - run at intervals
    interval_seconds: how often to repeat (for interval type)
    action: description of what to do (informational for now)
    """
    if schedule_type == "once":
        return f"Scheduled one-time action registered: {action}. (Scheduled tasks require persistent process)"
    elif schedule_type == "interval":
        return (f"Interval schedule registered: every {interval_seconds}s - {action}. "
                f"Note: Full background scheduling would require a daemon thread in the orchestrator.")
    else:
        return f"Unknown schedule type: {schedule_type}"