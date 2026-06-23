"""
Skynet Network Discovery — Automated host and service enumeration.
Scans a subnet, fingerprints services, and generates a comprehensive target list.
"""
import socket
import concurrent.futures
from datetime import datetime

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 389: "LDAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS",
    995: "POP3S", 1433: "MSSQL", 1521: "Oracle", 2049: "NFS",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    5985: "WinRM-HTTP", 5986: "WinRM-HTTPS", 6379: "Redis",
    8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 9090: "WebLogic",
    27017: "MongoDB"
}

def _resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return None

def _check_port(ip, port, timeout=2):
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def discover_network(subnet: str = "192.168.1.0/24", ports: str = None, max_workers: int = 50, timeout: int = 2) -> str:
    """
    Scan a subnet for active hosts and open ports, fingerprint services.
    
    Parameters:
    - subnet: CIDR notation (e.g. 192.168.1.0/24)
    - ports: Comma-separated list of ports. Default: common ports
    - max_workers: Parallel threads
    - timeout: Socket timeout per port
    """
    from ipaddress import ip_network
    try:
        network = ip_network(subnet)
    except ValueError:
        return f"Invalid subnet: {subnet}"
    
    ip_list = [str(ip) for ip in network.hosts()]
    
    if ports:
        port_list = sorted([int(p.strip()) for p in ports.split(",") if p.strip().isdigit()])
    else:
        port_list = sorted(COMMON_PORTS.keys())
    
    lines = [f"Skynet Network Discovery: {subnet}", f"Scanning {len(ip_list)} hosts...", "=" * 60]
    
    active_hosts = []
    
    def scan_host(ip):
        host_info = {"ip": ip, "hostname": None, "ports": []}
        
        # Resolve hostname
        hostname = _resolve_hostname(ip)
        if hostname:
            host_info["hostname"] = hostname
        
        # Scan ports
        open_ports = []
        for port in port_list:
            if _check_port(ip, port, timeout):
                service = COMMON_PORTS.get(port, "unknown")
                open_ports.append({"port": port, "service": service})
        
        if open_ports:
            host_info["ports"] = open_ports
            return host_info
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_host, ip): ip for ip in ip_list}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                active_hosts.append(result)
    
    # Sort by IP
    active_hosts.sort(key=lambda x: int(x["ip"].split('.')[-1]))
    
    if not active_hosts:
        lines.append("No active hosts found.")
        return "\n".join(lines)
    
    lines.append(f"Active hosts ({len(active_hosts)}):")
    lines.append(f"{'IP':<16} {'HOSTNAME':<25} {'PORTS':<30} {'SERVICES'}")
    lines.append("-" * 100)
    
    for host in active_hosts:
        ip = host["ip"]
        hostname = host["hostname"] or "unknown"
        ports_str = ", ".join(f"{p['port']}:{p['service']}" for p in host["ports"])
        services = ", ".join(sorted(set(p["service"] for p in host["ports"])))
        lines.append(f"{ip:<16} {hostname:<25} {ports_str:<30} {services}")
    
    lines.append(f"\nScan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)