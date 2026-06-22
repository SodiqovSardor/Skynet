import socket
import time

def raw_tcp_client(host: str, port: int, data: str = "", timeout: int = 10, read_first: bool = True) -> str:
    """
    Connect to a TCP service, optionally send data, and read response.
    
    Args:
        host: Target hostname or IP
        port: Target port
        data: Data to send (string). If empty, just reads banner.
        timeout: Socket timeout in seconds
        read_first: Read initial banner before sending data
    
    Returns:
        Full response text
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        
        result = ""
        
        # Read initial banner if requested
        if read_first:
            try:
                banner = sock.recv(4096).decode('utf-8', errors='replace')
                result += f"[BANNER] {banner}"
            except socket.timeout:
                pass
        
        # Send data if provided
        if data:
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            sock.sendall(data_bytes)
            result += f"\n[SENT {len(data_bytes)} bytes]\n"
            
            # Read response
            time.sleep(0.5)  # Give server time to respond
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    result += chunk.decode('utf-8', errors='replace')
            except socket.timeout:
                pass
        
        sock.close()
        
        if not result:
            return "[No response received]"
        return result.strip()
    
    except ConnectionRefusedError:
        return f"[Connection refused to {host}:{port}]"
    except socket.timeout:
        return f"[Connection timed out to {host}:{port}]"
    except Exception as e:
        return f"[Error: {str(e)}]"
