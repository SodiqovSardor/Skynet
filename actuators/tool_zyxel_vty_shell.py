"""
Zyxel VTY Shell - Full interactive session handler for Zyxel VTY consoles.
Handles the finicky protocol: reads banner, sends newline to get prompt,
then sends commands and captures multiline responses.
"""
import socket
import time
import re

def zyxel_vty_shell(target: str, port: int = 2601, command: str = "help", timeout: int = 15) -> str:
    """
    Connect to a Zyxel VTY console, handle the passwordless handshake,
    send a command, and return the full response.
    
    Args:
        target: IP or hostname of the target
        port: VTY port (default 2601)
        command: Command to execute on the VTY console
        timeout: Socket timeout in seconds
        
    Returns:
        String containing the full session output
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((target, port))
        
        # Read the initial banner
        banner = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                banner += chunk
                if b"password" in banner.lower() or b"Vty" in banner:
                    break
            except socket.timeout:
                break
        
        banner_str = banner.decode("utf-8", errors="replace")
        
        # Send newline to get past the password prompt (even when unset)
        time.sleep(0.5)
        sock.sendall(b"\r\n")
        
        # Read response after newline
        resp = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
                # Look for prompt indicators
                if b">" in chunk or b"#" in chunk or b"$" in chunk:
                    break
            except socket.timeout:
                break
        
        # Now send the actual command
        time.sleep(0.3)
        cmd_bytes = (command + "\r\n").encode()
        sock.sendall(cmd_bytes)
        
        # Read the command response
        output = b""
        start = time.time()
        while time.time() - start < 5:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                output += chunk
                # If we see the prompt again, we have the full response
                decoded = chunk.decode("utf-8", errors="replace")
                if re.search(r'[\w\-]+[>#$]', decoded):
                    # Wait a bit more for any trailing output
                    time.sleep(0.3)
                    try:
                        while True:
                            extra = sock.recv(4096)
                            if not extra:
                                break
                            output += extra
                    except socket.timeout:
                        break
                    break
            except socket.timeout:
                break
        
        full_output = output.decode("utf-8", errors="replace")
        
        # Clean up the output - remove control characters
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', full_output)
        clean = clean.strip()
        
        result = f"Banner: {banner_str.strip()}\n"
        if clean:
            result += f"Output: {clean}"
        else:
            result += "Output: (empty - command may not have produced output)"
        
        return result
        
    except socket.timeout:
        return f"Error: Connection timed out after {timeout}s"
    except ConnectionRefusedError:
        return f"Error: Connection refused to {target}:{port}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        try:
            sock.close()
        except:
            pass
