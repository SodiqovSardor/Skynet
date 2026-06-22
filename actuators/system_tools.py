import subprocess
import os
import sys
import importlib.util
import traceback
from typing import Any, Dict

# SANDBOX RESTRICTION
SANDBOX_ROOT = "/home/sadi/Skynet/sandbox"
ACTUATORS_DIR = os.path.dirname(os.path.abspath(__file__))

def _safe_path(path: str) -> str:
    """Ensures the path is within the sandbox directory."""
    if os.path.isabs(path):
        resolved = os.path.abspath(path)
    else:
        resolved = os.path.abspath(os.path.join(SANDBOX_ROOT, path))
    
    if not resolved.startswith(SANDBOX_ROOT):
        raise PermissionError(f"Access denied: {path} resolves to {resolved}, which is outside the sandbox.")
    return resolved

def run_shell_command(command: str) -> str:
    """Executes a shell command within the sandbox directory."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=SANDBOX_ROOT
        )
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(path: str) -> str:
    """Reads the content of a file within the sandbox.
    Only relative paths work (e.g. 'file.txt', 'subdir/file.txt').
    Absolute paths like /home/sadi/... are blocked by sandbox."""
    try:
        safe_path = _safe_path(path)
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except PermissionError as e:
        return f"BLOCKED: {e}. Use run_shell_command with cat/more instead for files outside sandbox."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Writes content to a file within the sandbox."""
    try:
        safe_path = _safe_path(path)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {safe_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def list_directory(path: str = ".") -> str:
    """Lists files in a directory within the sandbox."""
    try:
        safe_path = _safe_path(path)
        files = os.listdir(safe_path)
        return "\n".join(files) if files else "(empty)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def delete_file(path: str) -> str:
    """Deletes a file within the sandbox."""
    try:
        safe_path = _safe_path(path)
        os.remove(safe_path)
        return f"Successfully deleted {safe_path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"

def create_tool(name: str, code: str, function_name: str = None) -> str:
    """
    Creates a new tool by writing a Python file to actuators/ and registering it.
    
    Args:
        name: The tool name (e.g. 'scan_ports', 'download_file')
        code: Full Python source code implementing the tool function(s)
        function_name: The function to register (defaults to name)
    
    The code must define at least one function. That function becomes the tool.
    The tool is immediately available to Skynet.
    """
    try:
        if function_name is None:
            function_name = name
        
        filename = f"tool_{name}.py"
        filepath = os.path.join(ACTUATORS_DIR, filename)
        
        # Write the tool file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Dynamically import the module
        spec = importlib.util.spec_from_file_location(f"actuators.tool_{name}", filepath)
        if spec is None or spec.loader is None:
            return f"Error: Failed to load module from {filepath}"
        
        module = importlib.util.module_from_spec(spec)
        # Remove old module if it exists
        sys.modules.pop(f"actuators.tool_{name}", None)
        spec.loader.exec_module(module)
        
        # Get the function
        if not hasattr(module, function_name):
            return f"Error: Function '{function_name}' not found in {filename}. Available: {[x for x in dir(module) if not x.startswith('_')]}"
        
        func = getattr(module, function_name)
        
        # Register with the global registry
        from actuators.registry import registry
        registry.register_tool(name, func)
        
        return f"Tool '{name}' created and registered successfully. Function '{function_name}' from {filename} is now available."
    except Exception as e:
        return f"Error creating tool: {str(e)}\n{traceback.format_exc()}"

def list_tools() -> str:
    """Lists all currently registered tools with their names."""
    from actuators.registry import registry
    if not registry.tools:
        return "No tools registered."
    return "\n".join(f"  - {t}" for t in sorted(registry.tools.keys()))
