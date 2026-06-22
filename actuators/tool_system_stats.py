"""
System Stats Tool for Skynet.
Returns current system resource usage.
"""
import os
import platform
import psutil
from typing import Dict, Any

def get_system_stats() -> Dict[str, Any]:
    """Returns current system resource usage."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "os": platform.system(),
        "os_release": platform.release(),
        "disk_usage": psutil.disk_usage('/').percent
    }
