"""
Skynet Service Detector — Connects to open ports, grabs banners, and fingerprints services.
Combines banner_grab, port scanning, and heuristic detection for comprehensive service ID.
"""
import socket
import ssl
import time
import re
import concurrent.futures

COMMON_SERVICE_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    111: "RPC",
    135: "MSRPC",
    139: "NetBIOS",
    143: "IMAP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    2049: "NFS",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    5985: "WinRM-HTTP",
    5986: "WinRM-HTTPS",
    6379: "Redis",
    8080: "HTTP-Proxy",
    8443: "HTTPS-Alt",
    9090: "WebLogic",
    27017: "MongoDB",
}

SERVICE_PROBES = {
    21: b"HELP\r\n",
    22: b"",
    23: b"\r\n",
    25: b"EHLO probe\r\n",
    80: b"GET / HTTP/1.0\r\nHost: probe\r\n\r\n",
    110: b"",
    143: b"",
    443: b"",
    993: b"",
    995: b"",
    3306: b"",
    3389: b"",
    5432: b"",
    5900: b"",
    6379: b"PING\r\n",
    8080: b"GET / HTTP/1.0\r\nHost: probe\r\n\r\n",
    8443: b"",
    27017: b"",
}

def _grab_banner(host, port, timeout=5):
    """Connect to a port and grab the service banner."""
    banner = ""
    try:
        if port == 443:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    banner = ssock.recv(4096).decode("utf-8", errors="replace")[:500]
        else:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                # Send probe if available
                probe = SERVICE_PROBES.get(port)
                if probe:
                    try:
                        sock.sendall(probe)
                    except:
                        pass
                banner = sock.recv(4096).decode("utf-8", errors="replace")[:500]
    except ssl.SSLError:
        # Try non-SSL
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                probe = SERVICE_PROBES.get(port)
                if probe:
                    try:
                        sock.sendall(probe)
                    except:
                        pass
                banner = sock.recv(4096).decode("utf-8", errors="replace")[:500]
        except:
            pass
    except socket.timeout:
        banner = "(timeout)"
    except ConnectionRefusedError:
        return None  # Port not open
    except:
        pass
    
    return banner.strip()

def _fingerprint_service(port, banner):
    """Identify service from banner using known fingerprints."""
    if not banner or banner == "(timeout)":
        return COMMON_SERVICE_PORTS.get(port, "unknown")
    
    b = banner.lower()
    
    # SSH
    if re.search(r'ssh-\d+\.\d+|openssh', b):
        return "SSH"
    # FTP
    if re.search(r'ftp|220.*welcome|\bftp\b', b):
        return "FTP"
    # HTTP
    if re.search(r'http/1\.[01]|^get |^post |^head |server: |<!doctype|<html|<head|<title', b):
        m = re.search(r'server:\s*([^\r\n]+)', b, re.IGNORECASE)
        if m:
            return f"HTTP ({m.group(1).strip()})"
        return "HTTP"
    # SMTP
    if re.search(r'^220 |smtp|esmtp', b):
        return "SMTP"
    # POP3
    if re.search(r'^\+ok|pop3', b):
        return "POP3"
    # IMAP
    if re.search(r'^\* ok|imap', b):
        return "IMAP"
    # MySQL
    if re.search(r'mysql|mariadb', b):
        return "MySQL"
    # PostgreSQL
    if re.search(r'postgresql', b):
        return "PostgreSQL"
    # Redis
    if re.search(r'\+ok|\-err', b):
        return "Redis"
    # MongoDB
    if re.search(r'mongodb', b):
        return "MongoDB"
    # Telnet
    if re.search(r'telnet|^(\xff\xfb|\xff\xfd)', b):
        return "Telnet"
    # VNC
    if re.search(r'rf[bc]\d{3}\.|vnc', b):
        return "VNC"
    
    return COMMON_SERVICE_PORTS.get(port, "unknown")


def detect_services(host, ports=None, max_workers=20, timeout=5):
    """Scan a host and fingerprint services on specified or common ports.
    
    Parameters:
    - host: Target hostname or IP
    - ports: Comma-separated list of ports (e.g. '22,80,443') or empty for all common ports
    - max_workers: Number of parallel workers
    - timeout: Socket timeout in seconds
    """
    if ports:
        port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    else:
        port_list = list(COMMON_SERVICE_PORTS.keys())
    
    results = []
    
    def scan_port(port):
        result = _grab_banner(host, port, timeout)
        if result is None:
            return None  # Port closed
        service = _fingerprint_service(port, result)
        return {
            "port": port,
            "state": "open",
            "service": service,
            "banner": result[:200] if result else ""
        }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_port, p): p for p in port_list}
        for future in concurrent.futures.as_completed(futures):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except:
                pass
    
    results.sort(key=lambda x: x["port"])
    
    # Format output
    lines = [f"Service scan results for {host}:", "=" * 50]
    if not results:
        lines.append("No open ports found.")
    else:
        lines.append(f"{'PORT':<8} {'SERVICE':<30} {'BANNER'}")
        lines.append("-" * 60)
        for r in results:
            banner_short = r["banner"][:50].replace("\n", " ")
            lines.append(f"{r['port']:<8} {r['service']:<30} {banner_short}")
        
        lines.append("")
        lines.append(f"Total open ports: {len(results)}")
    
    return "\n".join(lines)
