"""
Skynet Sensors — Environment perception layer.

Sensors register themselves as tools upon import.
"""
from sensors.init import initialize_sensors
from sensors.system_sensors import get_system_stats, get_network_status

__all__ = ["initialize_sensors", "get_system_stats", "get_network_status"]
