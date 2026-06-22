import socket
def dns_lookup(hostname: str) -> str:
    """Perform DNS resolution for a hostname, returning all IP addresses."""
    try:
        ips = socket.gethostbyname_ex(hostname)
        return f"Hostname: {ips[0]}\nAliases: {ips[1]}\nAddresses: {ips[2]}"
    except Exception as e:
        return f"DNS lookup failed: {str(e)}"