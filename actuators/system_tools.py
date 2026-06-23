import subprocess
import os
import sys
import importlib.util
import traceback
import json
import re
from typing import Any, Dict, Optional

PROJECT_ROOT = "/home/sadi/Skynet"

# ── SAFETY BLOCKLIST ─────────────────────────────────────
# These patterns are FORBIDDEN regardless of who calls them.
# Protects the host system from accidental destruction.
_DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf /*", "rm -rf / ",
    "mkfs.", "dd if=", "format ",
    "> /dev/sd", "| sh", "| bash",
    "chmod 777 /", "chown -R /",
    "grub-install", "grub-mkconfig",
    "update-grub", "mkswap",
    "fdisk", "parted", "partprobe",
    "modprobe", "insmod", "rmmod",
    "systemctl stop ", "systemctl disable ",
    "pkill -9", "killall", "kill -9",
    "mv /lib", "mv /usr", "mv /etc",
    "rm /lib", "rm /usr", "rm /etc",
    "iptables -P", "iptables -F",
    "ufw ",
    "init 0", "init 6", "poweroff", "reboot", "shutdown",
    "passwd", "userdel", "groupdel",
]


def _is_safe_command(command: str) -> tuple:
    """Check if a command is safe to execute. Returns (safe, reason)."""
    cmd_lower = command.lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return False, f"BLOCKED: '{pattern}' is a forbidden destructive operation."
    return True, ""

def _safe_path(path: str) -> str:
    """Ensures the path is within the Skynet project directory."""
    if os.path.isabs(path):
        resolved = os.path.abspath(path)
    else:
        resolved = os.path.abspath(os.path.join(PROJECT_ROOT, path))
    
    if not resolved.startswith(PROJECT_ROOT):
        raise PermissionError(f"Access denied: {path} resolves to {resolved}, which is outside the project.")
    return resolved


def run_shell_command(command: str) -> str:
    """Executes any shell command. Use 'sudo:' prefix for sudo commands."""
    # Safety check
    safe, reason = _is_safe_command(command)
    if not safe:
        return f"SAFETY BLOCK: {reason}"
    try:
        cwd = PROJECT_ROOT
        if command.startswith("sudo:"):
            actual = command[5:].strip()
            # Check the actual command too
            safe2, reason2 = _is_safe_command(actual)
            if not safe2:
                return f"SAFETY BLOCK: {reason2}"
            result = subprocess.run(
                ["bash", "-c", f"echo btw | sudo -S -p '' {actual}"],
                capture_output=True, text=True, timeout=120, cwd=cwd
            )
        else:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd
            )
        out = f"STDOUT: {result.stdout}" if result.stdout else ""
        err = f"STDERR: {result.stderr}" if result.stderr else ""
        return (out + "\n" + err).strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s)"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def read_file(path: str) -> str:
    """Reads any file within the Skynet project directory."""
    try:
        safe = _safe_path(path)
        with open(safe, 'r', encoding='utf-8') as f:
            return f.read()
    except PermissionError as e:
        return f"BLOCKED: {e}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path: str, content: str) -> str:
    """Writes to any file within the Skynet project directory.
    Can modify core code, tools, configs, etc."""
    try:
        safe = _safe_path(path)
        os.makedirs(os.path.dirname(safe), exist_ok=True)
        with open(safe, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"OK: {os.path.relpath(safe, PROJECT_ROOT)} written ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_directory(path: str = ".") -> str:
    """Lists files in any directory under the project."""
    try:
        safe = _safe_path(path)
        items = os.listdir(safe)
        return "\n".join(sorted(items)) if items else "(empty)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def delete_file(path: str) -> str:
    """Deletes a file within the project directory."""
    try:
        safe = _safe_path(path)
        os.remove(safe)
        return f"Deleted: {os.path.relpath(safe, PROJECT_ROOT)}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


# ── NEW TIER 1 TOOLS ──────────────────────────────────────

def sudo_exec(command: str) -> str:
    """Execute a command with sudo. Password is pre-configured."""
    # Safety check
    safe, reason = _is_safe_command(command)
    if not safe:
        return f"SAFETY BLOCK: {reason}"
    try:
        result = subprocess.run(
            ["bash", "-c", f"echo btw | sudo -S -p '' {command}"],
            capture_output=True, text=True, timeout=120, cwd=PROJECT_ROOT
        )
        out = f"STDOUT: {result.stdout}" if result.stdout else ""
        err = f"STDERR: {result.stderr}" if result.stderr else ""
        return (out + "\n" + err).strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (120s)"
    except Exception as e:
        return f"Error executing sudo command: {str(e)}"


def install_package(package: str) -> str:
    """Install a system package (uses pacman on Arch Linux)."""
    # Auto-detect package manager
    if os.path.exists("/usr/bin/pacman"):
        return sudo_exec(f"pacman -S --noconfirm {package}")
    elif os.path.exists("/usr/bin/apt-get"):
        return sudo_exec(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {package}")
    elif os.path.exists("/usr/bin/dnf"):
        return sudo_exec(f"dnf install -y {package}")
    else:
        return f"Error: No known package manager found. Try sudo_exec directly."


def pip_install(package: str) -> str:
    """Install a Python package in the Skynet venv."""
    try:
        python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
        result = subprocess.run(
            [python, "-m", "pip", "install", package],
            capture_output=True, text=True, timeout=120, cwd=PROJECT_ROOT
        )
        stdout = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
        stderr = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
        return f"pip install {package}:\n{stdout}\n{stderr}".strip()
    except Exception as e:
        return f"Error installing Python package: {str(e)}"


def switch_model(model_name: str) -> str:
    """Switch the AI model at runtime. Next thinking cycle uses the new model.
    Available: big-pickle, deepseek-v4-flash-free, mimo-v2.5-free, north-mini-code-free, nemotron-3-ultra-free"""
    try:
        from core.brain import switch_active_model
        return switch_active_model(model_name)
    except Exception as e:
        return f"Error switching model: {str(e)}"


def list_available_models() -> str:
    """List all models available on the API provider."""
    models = [
        "deepseek-v4-flash-free",
        "big-pickle",
        "mimo-v2.5-free",
        "north-mini-code-free",
        "nemotron-3-ultra-free"
    ]
    # Try to fetch live model list
    try:
        import requests
        r = requests.get("https://opencode.ai/zen/v1/models", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                models = [m["id"] for m in data["data"]]
    except:
        pass
    return "\n".join(f"  - {m}" for m in models)


# ── TIER 2 TOOLS ─────────────────────────────────────────

def start_http_server(port: int = 8080, directory: str = ".") -> str:
    """Start a background HTTP server on the given port."""
    try:
        safe = _safe_path(directory)
        pid = os.fork()
        if pid == 0:
            os.chdir(safe)
            os.execvp("python3", ["python3", "-m", "http.server", str(port)])
        return f"HTTP server started on port {port} (PID {pid}), serving {safe}"
    except Exception as e:
        return f"Error starting HTTP server: {str(e)}"


def ssh_client(host: str, username: str, password: str, command: str) -> str:
    """SSH into a remote host and execute a command."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=10)
        _, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        client.close()
        return f"STDOUT: {out}\nSTDERR: {err}".strip()
    except ImportError:
        return "Error: paramiko not installed. Use sudo_exec('pip install paramiko') first."
    except Exception as e:
        return f"SSH error: {str(e)}"


def send_telegram(message: str, bot_token: str = None, chat_id: str = None) -> str:
    """Send a Telegram notification. Set bot_token and chat_id via env vars or params."""
    try:
        token = bot_token or os.environ.get("SKYNET_TELEGRAM_TOKEN")
        cid = chat_id or os.environ.get("SKYNET_TELEGRAM_CHAT_ID")
        if not token or not cid:
            # Fallback: read from .env file
            env_path = os.path.join(PROJECT_ROOT, ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("SKYNET_TELEGRAM_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip("'\"")
                        elif line.startswith("SKYNET_TELEGRAM_CHAT_ID="):
                            cid = line.split("=", 1)[1].strip().strip("'\"")
        if not token or not cid:
            return "Error: Telegram credentials not found in env vars or .env file."
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": cid, "text": message}
        )
        if r.status_code == 200:
            return "Telegram message sent."
        return f"Telegram error: {r.status_code} {r.text}"
    except Exception as e:
        return f"Telegram error: {str(e)}"


# ── TIER 3 TOOLS ─────────────────────────────────────────

def schedule_cron(command: str, schedule: str = "@hourly", label: str = "skynet_task") -> str:
    """Schedule a cron job. Schedule in cron format or @hourly/@daily/@reboot."""
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        current = existing.stdout if existing.returncode == 0 else ""
        
        # Remove any existing entry with same label
        lines = [l for l in current.split("\n") if label not in l]
        
        # Add new entry
        lines.append(f"# {label}")
        lines.append(f"{schedule} cd {PROJECT_ROOT} && {command}")
        
        new_cron = "\n".join(lines) + "\n"
        proc = subprocess.run(
            ["bash", "-c", f"echo btw | sudo -S -p '' crontab -"],
            input=new_cron, capture_output=True, text=True, timeout=10
        )
        if proc.returncode == 0:
            return f"Cron job scheduled: {schedule} {command}"
        return f"Cron error: {proc.stderr}"
    except Exception as e:
        return f"Error scheduling cron: {str(e)}"


def install_persistence() -> str:
    """Install a systemd user service so Skynet restarts on boot and after crashes."""
    try:
        service_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(service_dir, exist_ok=True)
        
        service = f"""[Unit]
Description=Skynet Autonomous Agent
After=network.target

[Service]
Type=simple
ExecStart={PROJECT_ROOT}/venv/bin/python -m core.autonomous_orchestrator
WorkingDirectory={PROJECT_ROOT}
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
        path = os.path.join(service_dir, "skynet.service")
        with open(path, "w") as f:
            f.write(service)
        
        subprocess.run(
            ["bash", "-c", f"echo btw | sudo -S -p '' systemctl --user daemon-reload && systemctl --user enable skynet"],
            capture_output=True, text=True, timeout=15, cwd=PROJECT_ROOT
        )
        return f"Persistence installed. Start with: systemctl --user start skynet\nService file: {path}"
    except Exception as e:
        return f"Error installing persistence: {str(e)}"


# ── ORIGINAL create_tool / list_tools ─────────────────────

def create_tool(name: str, code: str, function_name: str = None) -> str:
    """Creates a new tool by writing a Python file to actuators/ and registering it."""
    try:
        if function_name is None:
            function_name = name
        
        ACTUATORS_DIR = os.path.dirname(os.path.abspath(__file__))
        filename = f"tool_{name}.py"
        filepath = os.path.join(ACTUATORS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        spec = importlib.util.spec_from_file_location(f"actuators.tool_{name}", filepath)
        if spec is None or spec.loader is None:
            return f"Error: Failed to load module from {filepath}"
        
        module = importlib.util.module_from_spec(spec)
        sys.modules.pop(f"actuators.tool_{name}", None)
        spec.loader.exec_module(module)
        
        if not hasattr(module, function_name):
            return f"Error: Function '{function_name}' not found. Available: {[x for x in dir(module) if not x.startswith('_')]}"
        
        func = getattr(module, function_name)
        
        from actuators.registry import registry
        registry.register_tool(name, func)
        
        return f"Tool '{name}' created and registered successfully."
    except Exception as e:
        return f"Error creating tool: {str(e)}\n{traceback.format_exc()}"


def list_tools() -> str:
    """Lists all currently registered tools."""
    from actuators.registry import registry
    if not registry.tools:
        return "No tools registered."
    return "\n".join(f"  - {t}" for t in sorted(registry.tools.keys()))
