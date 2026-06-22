"""
Network Scanner Tool for Skynet.
Performs port scanning and network reconnaissance.
"""
import socket
import subprocess
import json
from typing import List, Dict, Any

def network_scan(target: str, ports: str = "1-1024") -> str:
    """
    Scans a target host for open ports.
    
    Args:
        target: IP address or hostname to scan
        ports: Port range like "80", "80,443", "1-1024"
    
    Returns:
        Scan results as formatted string
    """
    results = []
    
    if "-" in ports:
        start, end = ports.split("-")
        port_range = range(int(start), int(end) + 1)
    elif "," in ports:
        port_range = [int(p.strip()) for p in ports.split(",")]
    else:
        port_range = [int(ports)]
    
    try:
        ip = socket.gethostbyname(target)
    except socket.gaierror:
        return f"Error: Could not resolve hostname '{target}'"
    
    results.append(f"Target: {target} ({ip})")
    results.append(f"Scanning ports: {len(port_range)} ports")
    results.append("---")
    
    open_ports = []
    for port in port_range:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                service = "unknown"
                try:
                    service = socket.getservbyport(port)
                except:
                    pass
                open_ports.append((port, service))
        except Exception:
            pass
    
    if open_ports:
        for port, service in open_ports:
            results.append(f"  PORT {port:5d} OPEN  {service}")
    else:
        results.append("  No open ports found in range.")
    
    results.append(f"\nSummary: {len(open_ports)}/{len(port_range)} ports open")
    
    return "\n".join(results)