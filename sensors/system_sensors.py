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

def get_network_status() -> str:
    """Checks if the system has internet connectivity."""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return "Connected"
    except OSError:
        return "Disconnected"
