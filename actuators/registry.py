from typing import Any, Dict, Callable, List
from actuators.system_tools import *

class ToolRegistry:
    """
    Registry that maps tool names to their Python implementations.
    Supports hot-reloading of tools created at runtime.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register_tool("run_shell_command", run_shell_command)
        self.register_tool("read_file", read_file)
        self.register_tool("write_file", write_file)
        self.register_tool("list_directory", list_directory)
        self.register_tool("delete_file", delete_file)
        self.register_tool("create_tool", create_tool)
        self.register_tool("list_tools", list_tools)

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def unregister_tool(self, name: str):
        self.tools.pop(name, None)

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self.tools:
            return f"Error: Tool '{name}' not found. Available tools: {', '.join(sorted(self.tools.keys()))}"
        
        try:
            return self.tools[name](**arguments)
        except TypeError as e:
            return f"Error: Invalid arguments for tool '{name}'. {str(e)}"
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

# Global registry instance
registry = ToolRegistry()
