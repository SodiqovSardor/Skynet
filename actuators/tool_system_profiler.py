"""
Advanced System Profiler for Skynet.
Gathers detailed system information beyond basic stats.
"""
import os
import platform
import subprocess
import json
import socket
import datetime

def system_profiler() -> str:
    """
    Gathers comprehensive system information.
    
    Returns:
        JSON string with detailed system profile
    """
    info = {}
    
    info['os'] = {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'hostname': socket.gethostname(),
        'python_version': platform.python_version(),
    }
    
    try:
        info['user'] = {
            'current_user': os.environ.get('USER', 'unknown'),
            'home': os.environ.get('HOME', 'unknown'),
            'shell': os.environ.get('SHELL', 'unknown'),
            'uid': os.getuid(),
            'gid': os.getgid(),
        }
    except:
        pass
    
    try:
        import psutil
        proc_count = len(psutil.pids())
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat()
        info['processes'] = {
            'total': proc_count,
            'boot_time': boot_time,
        }
        info['cpu'] = {
            'cores': psutil.cpu_count(),
            'physical_cores': psutil.cpu_count(logical=False),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else 'unknown',
        }
        info['memory'] = {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
        }
        info['disk'] = {
            'total': psutil.disk_usage('/').total,
            'used': psutil.disk_usage('/').used,
        }
    except:
        pass
    
    try:
        with open('/proc/mounts', 'r') as f:
            mounts = f.read().split('\n')[:30]
            info['mounts'] = mounts
    except:
        pass
    
    env_vars = {}
    for key, value in sorted(os.environ.items()):
        if not any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password', 'auth']):
            env_vars[key] = value[:100] if len(value) > 100 else value
    info['environment'] = env_vars
    
    return json.dumps(info, indent=2)