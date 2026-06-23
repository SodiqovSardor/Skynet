"""
Zyxel Config Dump - Extract full gateway configuration via VTY console.
Connects to the passwordless VTY, runs a series of commands to dump
system info, network config, firewall rules, DNS, DHCP, users, and more.
"""
import socket
import time
import re


def _vty_send_command(sock, cmd, timeout=5):
    """Send a command and read the response."""
    sock.sendall((cmd + "\r\n").encode())
    output = b""
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            output += chunk
            # Check for prompt
            decoded = chunk.decode("utf-8", errors="replace")
            if re.search(r'[\w\-]+[>#$]\s*$', decoded):
                # Got prompt, grab any trailing data
                time.sleep(0.2)
                try:
                    while True:
                        extra = sock.recv(4096)
                        if not extra:
                            break
                        output += extra
                except socket.timeout:
                    pass
                break
        except socket.timeout:
            break
    return output.decode("utf-8", errors="replace")


def zyxel_config_dump(target: str, port: int = 2601, timeout: int = 30) -> str:
    """
    Connect to a Zyxel VTY console and extract the full gateway configuration.
    Runs a comprehensive set of commands to dump system state.
    
    Args:
        target: IP address of the Zyxel gateway
        port: VTY console port (default 2601)
        timeout: Overall timeout in seconds
        
    Returns:
        String containing the full configuration dump
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((target, port))
        
        # Read banner
        banner = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                banner += chunk
            except socket.timeout:
                break
        
        # Send newline to get past any prompt
        time.sleep(0.5)
        sock.sendall(b"\r\n")
        time.sleep(0.5)
        
        # Clear any initial output
        try:
            sock.recv(4096)
        except:
            pass
        
        commands = [
            "show system-info",
            "show interface ethernet",
            "show interface vlan",
            "show ip route",
            "show ip dns",
            "show dhcp server",
            "show firewall policy",
            "show nat rule",
            "show users",
            "show running-config",
            "show log",
        ]
        
        results = [f"=== ZYXEL GATEWAY CONFIG DUMP (target: {target}:{port}) ==="]
        results.append(f"Banner: {banner.decode('utf-8', errors='replace').strip()}")
        results.append("")
        
        for cmd in commands:
            results.append(f">>> {cmd}")
            time.sleep(0.3)
            try:
                output = _vty_send_command(sock, cmd, timeout=5)
                if output.strip():
                    results.append(output.strip())
                else:
                    results.append("(no output)")
            except socket.timeout:
                results.append("(timeout)")
            except Exception as e:
                results.append(f"(error: {e})")
            results.append("")
        
        return "\n".join(results)
        
    except socket.timeout:
        return f"Error: Connection timed out to {target}:{port}"
    except ConnectionRefusedError:
        return f"Error: Connection refused to {target}:{port}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        try:
            sock.close()
        except:
            pass
