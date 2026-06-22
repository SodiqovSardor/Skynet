"""
Tool Registry for Skynet.
Auto-discovers and registers all tools from the actuators directory.
Generates OpenAI-compatible schemas for every registered tool.
"""
import os
import sys
import inspect
import types
import json
import importlib
from typing import Any, Dict, Callable, Optional, List, get_type_hints, get_origin, get_args

# Directory where actuator tool files live
ACTUATORS_DIR = os.path.dirname(os.path.abspath(__file__))

# Names to skip during auto-discovery (common imports, type hints)
SKIP_NAMES = {
    'Any', 'Dict', 'List', 'Optional', 'Tuple', 'Set', 
    'Type', 'Union', 'Iterator', 'Iterable', 'Sequence', 'Mapping',
    'str', 'int', 'float', 'bool', 'None', 'True', 'False',
    'os', 'sys', 'json', 'time', 'socket', 'subprocess', 'platform',
    're', 'math', 'random', 'datetime', 'pathlib', 'shutil', 'glob',
    'logging', 'traceback', 'inspect', 'functools', 'itertools',
    'collections', 'contextlib', 'typing', 'importlib',
}

# Python type → JSON Schema type mapping
TYPE_MAP = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    type(None): {"type": "null"},
}


def _type_to_schema(tp):
    """Convert a Python type annotation to a JSON Schema property."""
    origin = get_origin(tp)
    args = get_args(tp)
    
    # Handle Optional[X] = Union[X, None]
    if origin is type(Optional[str]) and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            schema = _type_to_schema(non_none[0])
            return schema
        return {"type": "string"}
    
    # Handle List[X], Dict[K,V], etc.
    if origin is list:
        if args:
            return {"type": "array", "items": _type_to_schema(args[0])}
        return {"type": "array"}
    if origin is dict:
        return {"type": "object"}
    if origin is tuple:
        return {"type": "array"}
    
    # Handle Union types (simplify to first viable)
    if origin is type(Optional[str]) or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _type_to_schema(non_none[0])
        return {"type": "string"}
    
    # Basic types
    for py_type, schema in TYPE_MAP.items():
        if tp is py_type:
            return schema
    
    # Fallback: check if it's a class with __name__
    if hasattr(tp, "__name__"):
        name = tp.__name__.lower()
        if name == "str":
            return {"type": "string"}
        if name in ("int", "float"):
            return {"type": "number"}
        if name == "bool":
            return {"type": "boolean"}
        if name == "dict":
            return {"type": "object"}
        if name == "list":
            return {"type": "array"}
        # Any other named type
        return {"type": "string"}
    
    return {"type": "string"}  # fallback


def _generate_schema(func) -> Dict[str, Any]:
    """Generate an OpenAI-compatible function schema from a Python function."""
    sig = inspect.signature(func)
    hints = {}
    try:
        hints = get_type_hints(func) or {}
    except Exception:
        pass
    
    properties = {}
    required = []
    
    for name, param in sig.parameters.items():
        if name == "self" or name == "cls":
            continue
        
        type_hint = hints.get(name, str)
        schema = _type_to_schema(type_hint)
        
        # Add description from docstring param hints
        description = f"Parameter: {name}"
        
        prop = {**schema}
        if description:
            prop["description"] = description
        
        properties[name] = prop
        
        # Required if no default value
        if param.default is inspect.Parameter.empty:
            required.append(name)
    
    # Get description from docstring
    description = (func.__doc__ or "").strip()
    if description:
        # Take only the first line/sentence
        description = description.split("\n")[0].strip()
    else:
        description = f"Execute the {func.__name__} tool"
    
    return {
        "description": description[:200],
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    }


class ToolRegistry:
    """
    Registry that maps tool names to their Python implementations.
    Supports hot-reloading of tools created at runtime.
    Auto-discovers tools from actuator files on initialization.
    Generates OpenAI-compatible schemas for every tool.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
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
            
            module_name = filename[:-3]
            filepath = os.path.join(ACTUATORS_DIR, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(
                    f"actuators.{module_name}", filepath
                )
                if spec is None or spec.loader is None:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
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
        """Register a tool and generate its schema."""
        self.tools[name] = func
        try:
            self.schemas[name] = _generate_schema(func)
        except Exception as e:
            self.schemas[name] = {
                "description": f"Execute {name}",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }

    def unregister_tool(self, name: str):
        self.tools.pop(name, None)
        self.schemas.pop(name, None)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return all tool definitions in OpenAI API format."""
        definitions = []
        for name in sorted(self.tools.keys()):
            schema = self.schemas.get(name, {})
            definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.get("description", f"Execute {name}"),
                    "parameters": schema.get("parameters", {
                        "type": "object", "properties": {}, "required": []
                    }),
                }
            })
        return definitions

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self.tools:
            return f"Error: Tool '{name}' not found. Available tools: {', '.join(sorted(self.tools.keys()))}"
        
        try:
            return self.tools[name](**arguments)
        except TypeError as e:
            sig = inspect.signature(self.tools[name])
            return f"Error: Invalid arguments for tool '{name}'. Expected {sig}. Error: {str(e)}"
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

# Global registry instance
registry = ToolRegistry()
