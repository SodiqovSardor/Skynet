import socket

def banner_grab(host: str, port: int, timeout: float = 5.0) -> str:
    """
    Connect to a service and grab its banner.
    Returns the banner text or an error message.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        
        # Send a generic probe for services that expect input
        try:
            sock.send(b"GET / HTTP/1.0\r\n\r\n")
        except:
            pass
        
        # Try to receive banner
        banner = b""
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                banner += data
                if len(banner) > 8192:
                    break
        except socket.timeout:
            pass
        
        sock.close()
        
        if banner:
            # Try to decode, replacing non-printable chars
            decoded = banner.decode("utf-8", errors="replace")
            return f"Banner from {host}:{port}:\n{decoded[:2000]}"
        else:
            return f"{host}:{port} - Connected but no banner received"
            
    except socket.timeout:
        return f"{host}:{port} - Connection timed out"
    except ConnectionRefusedError:
        return f"{host}:{port} - Connection refused"
    except socket.gaierror:
        return f"{host}:{port} - Hostname resolution failed"
    except Exception as e:
        return f"{host}:{port} - Error: {str(e)}"