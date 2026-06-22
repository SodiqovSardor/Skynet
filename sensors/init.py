from sensors.system_sensors import get_system_stats, get_network_status
from actuators.registry import registry

def initialize_sensors():
    """Registers sensor functions as tools in the registry."""
    registry.register_tool("get_system_stats", get_system_stats)
    registry.register_tool("get_network_status", get_network_status)

# Initialize sensors immediately upon import
initialize_sensors()
