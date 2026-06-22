"""
Network Sweep Tool for Skynet.
Discovers active hosts on the local subnet using ARP ping and basic port checks.
"""
import subprocess
import socket
import ipaddress
import json
from typing import List, Dict, Any
import concurrent.futures

def _ping_host(ip: str) -> bool:
    """Check if a host is reachable via ICMP ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False

def _check_port(ip: str, port: int) -> bool:
    """Check if a specific port is open on a host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def network_sweep(subnet: str = "192.168.1.0/24", ports: str = "22,80,443,8080") -> str:
    """
    Sweep a subnet for active hosts and open ports.
    
    Args:
        subnet: CIDR notation subnet to scan (e.g., "192.168.1.0/24")
        ports: Comma-separated list of ports to check on each host
    
    Returns:
        JSON string with discovered hosts
    """
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as e:
        return f"Error: Invalid subnet '{subnet}'. {str(e)}"
    
    port_list = [int(p.strip()) for p in ports.split(",")]
    
    # Get all IPs in subnet (excluding network and broadcast)
    hosts = [str(ip) for ip in network.hosts()]
    
    results = {
        "subnet": subnet,
        "total_hosts": len(hosts),
        "active_hosts": [],
        "scan_time": 0
    }
    
    import time
    start = time.time()
    
    # Ping sweep in parallel
    active_ips = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ip = {executor.submit(_ping_host, ip): ip for ip in hosts}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                if future.result():
                    active_ips.append(ip)
            except:
                pass
    
    # Port scan active hosts
    for ip in active_ips:
        host_info = {
            "ip": ip,
            "hostname": "unknown",
            "ports": []
        }
        try:
            host_info["hostname"] = socket.gethostbyaddr(ip)[0]
        except:
            pass
        
        for port in port_list:
            if _check_port(ip, port):
                service = "unknown"
                try:
                    service = socket.getservbyport(port)
                except:
                    pass
                host_info["ports"].append({"port": port, "service": service})
        
        results["active_hosts"].append(host_info)
    
    results["scan_time"] = time.time() - start
    results["active_count"] = len(active_ips)
    
    return json.dumps(results, indent=2)
