"""
Skynet Port Monitor — Continuously monitors a target's open ports over time.
Tracks changes (new open ports, closed ports) and reports differences.
"""
import socket
import time
import json
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Optional

def _check_port(host: str, port: int, timeout: float = 3) -> tuple:
    """Check if a single port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            return (port, True)
    except (socket.timeout, ConnectionRefusedError, OSError):
        return (port, False)

def _scan_ports(host: str, ports: List[int], timeout: float = 3, workers: int = 50) -> Dict[int, bool]:
    """Scan a list of ports and return {port: open} dict."""
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_check_port, host, p, timeout): p for p in ports}
        for future in concurrent.futures.as_completed(futures):
            port, is_open = future.result()
            results[port] = is_open
    return results

def monitor_ports(host: str, ports: str = None, iterations: int = 3, interval: int = 10, timeout: int = 3) -> str:
    """
    Monitor a set of ports on a host over multiple scans and report changes.
    
    Parameters:
    - host: Target hostname or IP
    - ports: Comma-separated list of ports (e.g. '22,80,443'). Default: common ports
    - iterations: Number of scan iterations to run
    - interval: Seconds between scans
    - timeout: Socket timeout per port
    """
    common_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 389, 443, 445, 
                    993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 5900, 5985, 5986, 
                    6379, 8080, 8443, 9090, 27017]
    
    if ports:
        port_list = sorted([int(p.strip()) for p in ports.split(",") if p.strip().isdigit()])
    else:
        port_list = common_ports
    
    lines = [f"🔍 Port Monitor — {host}", f"Iterations: {iterations}, Interval: {interval}s", "=" * 60]
    
    previous = {}
    change_log = []
    
    for i in range(iterations):
        timestamp = datetime.now().strftime("%H:%M:%S")
        lines.append(f"\n--- Scan {i+1}/{iterations} at {timestamp} ---")
        
        current = _scan_ports(host, port_list, timeout)
        open_ports = [p for p, state in current.items() if state]
        
        if open_ports:
            lines.append(f"Open ports ({len(open_ports)}): {', '.join(map(str, sorted(open_ports)))}")
        else:
            lines.append("No open ports detected.")
        
        # Compare with previous scan
        if previous:
            newly_open = [p for p in open_ports if p not in previous or not previous[p]]
            newly_closed = [p for p in previous if previous[p] and p not in current or (p in current and not current[p])]
            
            if newly_open:
                msg = f"🟢 NEW OPEN: {', '.join(map(str, newly_open))}"
                lines.append(f"  {msg}")
                change_log.append(msg)
            if newly_closed:
                msg = f"🔴 CLOSED: {', '.join(map(str, newly_closed))}"
                lines.append(f"  {msg}")
                change_log.append(msg)
            if not newly_open and not newly_closed:
                lines.append("  No changes detected.")
        
        previous = current
        
        if i < iterations - 1:
            time.sleep(interval)
    
    if change_log:
        lines.append("\n📋 Change Summary:")
        for c in change_log:
            lines.append(f"  {c}")
    else:
        lines.append("\n📋 No port state changes detected across all scans.")
    
    return "\n".join(lines)
