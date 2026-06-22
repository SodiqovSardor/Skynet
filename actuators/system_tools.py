import subprocess
import os
import shutil
from typing import Any, Dict

# SANDBOX RESTRICTION
SANDBOX_ROOT = "/home/sadi/Skynet/sandbox"

def _safe_path(path: str) -> str:
    """Ensures the path is within the sandbox directory."""
    # Resolve the path to an absolute path
    if os.path.isabs(path):
        # Absolute path: check if it's inside the sandbox
        resolved = os.path.abspath(path)
    else:
        # Relative path: resolve relative to SANDBOX_ROOT
        resolved = os.path.abspath(os.path.join(SANDBOX_ROOT, path))
    
    if not resolved.startswith(SANDBOX_ROOT):
        raise PermissionError(f"Access denied: {path} resolves to {resolved}, which is outside the sandbox.")
    return resolved

def run_shell_command(command: str) -> str:
    """Executes a shell command within the sandbox directory."""
    try:
        # We change the working directory to the sandbox for the command
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
    """Reads the content of a file within the sandbox."""
    try:
        safe_path = _safe_path(path)
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
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
        return "\n".join(files)
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
