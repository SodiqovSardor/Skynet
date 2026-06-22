"""
Network Status Tool for Skynet.
Checks internet connectivity.
"""
import socket

def get_network_status() -> str:
    """Checks if the system has internet connectivity."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return "Connected"
    except OSError:
        return "Disconnected"
