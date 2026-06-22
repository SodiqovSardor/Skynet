"""
Tool Registry for Skynet.
Auto-discovers and registers all tools from the actuators directory.
"""
import os
import sys
import importlib.util
import types
from typing import Any, Dict, Callable

# Directory where actuator tool files live
ACTUATORS_DIR = os.path.dirname(os.path.abspath(__file__))

# Names to skip during auto-discovery (common imports, type hints)
SKIP_NAMES = {
    'Any', 'Dict', 'List', 'Optional', 'Callable', 'Tuple', 'Set', 
    'Type', 'Union', 'Iterator', 'Iterable', 'Sequence', 'Mapping',
    'str', 'int', 'float', 'bool', 'None', 'True', 'False',
    'os', 'sys', 'json', 'time', 'socket', 'subprocess', 'platform',
    're', 'math', 'random', 'datetime', 'pathlib', 'shutil', 'glob',
    'logging', 'traceback', 'inspect', 'functools', 'itertools',
    'collections', 'contextlib', 'typing', 'importlib',
}

class ToolRegistry:
    """
    Registry that maps tool names to their Python implementations.
    Supports hot-reloading of tools created at runtime.
    Auto-discovers tools from actuator files on initialization.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_core_tools()
        self._discover_tool_files()

    def _register_core_tools(self):
        """Register the core tools from system_tools."""
        from actuators.system_tools import (
            run_shell_command, read_file, write_file,
            list_directory, delete_file, create_tool, list_tools
        )
        self.register_tool("run_shell_command", run_shell_command)
        self.register_tool("read_file", read_file)
        self.register_tool("write_file", write_file)
        self.register_tool("list_directory", list_directory)
        self.register_tool("delete_file", delete_file)
        self.register_tool("create_tool", create_tool)
        self.register_tool("list_tools", list_tools)

    def _discover_tool_files(self):
        """Scan actuators directory for tool_*.py files and register their functions."""
        if not os.path.isdir(ACTUATORS_DIR):
            return
        
        for filename in sorted(os.listdir(ACTUATORS_DIR)):
            if not filename.startswith("tool_") or not filename.endswith(".py"):
                continue
            if filename == "__init__.py":
                continue
            
            module_name = filename[:-3]  # Remove .py
            filepath = os.path.join(ACTUATORS_DIR, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(
                    f"actuators.{module_name}", filepath
                )
                if spec is None or spec.loader is None:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Register only functions defined IN this module (not imported)
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    if attr_name in SKIP_NAMES:
                        continue
                    if attr_name in self.tools:
                        continue
                    
                    attr = getattr(module, attr_name)
                    if not isinstance(attr, types.FunctionType):
                        continue
                    if attr.__module__ != module_name and attr.__module__ != f"actuators.{module_name}":
                        continue
                    
                    self.register_tool(attr_name, attr)
                    
            except Exception as e:
                print(f"[Registry] Error loading {filename}: {e}")

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
