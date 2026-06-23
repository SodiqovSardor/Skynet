"""
Zyxel Web Crypto Login - Handles JSEncrypt/AES encrypted login for Zyxel gateways.
Extracts RSA public key from the page, encrypts password, and authenticates.
"""
import requests
import re
import json
import base64
import math
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def _extract_public_key(html):
    """Extract RSA public key modulus and exponent from embedded JS."""
    # Look for RSA key parameters in various patterns
    patterns = [
        (r'var\s+rsa_modulus\s*=\s*["\']([^"\']+)', r'var\s+rsa_exponent\s*=\s*["\']([^"\']+)'),
        (r'modulus\s*:\s*["\']([^"\']+)', r'exponent\s*:\s*["\']([^"\']+)'),
        (r'"modulus"\s*:\s*"([^"]+)"', r'"exponent"\s*:\s*"([^"]+)"'),
        (r'rsaModulus\s*=\s*["\']([^"\']+)', r'rsaExponent\s*=\s*["\']([^"\']+)'),
        (r'publicKeyModulus\s*=\s*["\']([^"\']+)', r'publicKeyExponent\s*=\s*["\']([^"\']+)'),
    ]
    
    for mod_pat, exp_pat in patterns:
        mod_match = re.search(mod_pat, html, re.IGNORECASE)
        exp_match = re.search(exp_pat, html, re.IGNORECASE)
        if mod_match and exp_match:
            return mod_match.group(1), exp_match.group(1)
    
    # Try PEM format
    pem_match = re.search(r'-----BEGIN PUBLIC KEY-----([^<]+)-----END PUBLIC KEY-----', html)
    if pem_match:
        return pem_match.group(0).strip(), None
    
    return None, None


def _rsa_encrypt(password, modulus_hex, exponent_hex):
    """Encrypt password using RSA with given modulus and exponent."""
    modulus = int(modulus_hex, 16)
    exponent = int(exponent_hex, 16)
    
    public_numbers = rsa.RSAPublicNumbers(exponent, modulus)
    public_key = public_numbers.public_key(default_backend())
    
    ciphertext = public_key.encrypt(
        password.encode(),
        padding.PKCS1v15()
    )
    
    return base64.b64encode(ciphertext).decode()


def _try_direct_login(session, base_url, username, password, result_lines):
    """Try direct (unencrypted) login."""
    login_data = {
        "username": username,
        "password": password,
    }
    
    for endpoint in ["/cgi-bin/login", "/login.cgi", "/cgi-bin/luci"]:
        try:
            resp = session.post(f"{base_url}{endpoint}", data=login_data, timeout=10)
            result_lines.append(f"Direct login to {endpoint}: HTTP {resp.status_code}")
            if resp.status_code == 200:
                if "success" in resp.text.lower() or "logout" in resp.text.lower() or "dashboard" in resp.text.lower():
                    result_lines.append(f">> LOGIN SUCCESSFUL!")
                    result_lines.append(f"Cookies: {dict(session.cookies)}")
                    result_lines.append(f"Response: {resp.text[:300]}")
                    return "\n".join(result_lines)
                elif len(resp.text) > 100:
                    result_lines.append(f"  Got response ({len(resp.text)} bytes)")
        except Exception as e:
            result_lines.append(f"  Error: {e}")
    
    return None


def zyxel_web_crypto_login(target: str, username: str = "admin", password: str = "", port: int = 80, use_https: bool = False) -> str:
    """
    Attempt to login to a Zyxel gateway with RSA-encrypted password handling.
    
    Args:
        target: IP address
        username: Login username (default: admin)
        password: Password to try
        port: HTTP port (default: 80)
        use_https: Use HTTPS (default: False)
        
    Returns:
        Full login result
    """
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{target}:{port}"
    
    session = requests.Session()
    session.verify = False
    
    result_lines = []
    result_lines.append(f"=== Zyxel Crypto Login ===")
    result_lines.append(f"Target: {base_url}")
    result_lines.append(f"Username: {username}")
    result_lines.append(f"Password: {'*' * len(password) if password else '(empty)'}")
    result_lines.append("")
    
    # Step 1: Get the login page
    try:
        resp = session.get(f"{base_url}/", timeout=10)
        html = resp.text
        result_lines.append(f"Page loaded: HTTP {resp.status_code} ({len(html)} bytes)")
    except Exception as e:
        return f"Failed to load page: {e}"
    
    # Step 2: Extract RSA public key
    modulus, exponent = _extract_public_key(html)
    sources_checked = ["main page"]
    
    if not (modulus and exponent):
        # Try loading JS files referenced in the page
        js_files = re.findall(r'src=[\'"]([^\'"]+\.js)[\'"]', html)
        for js_file in js_files:
            js_url = js_file if js_file.startswith('http') else (
                f"{base_url}{js_file}" if js_file.startswith('/') else f"{base_url}/{js_file}"
            )
            try:
                js_resp = session.get(js_url, timeout=10)
                js_content = js_resp.text
                modulus, exponent = _extract_public_key(js_content)
                sources_checked.append(js_file)
                if modulus and exponent:
                    result_lines.append(f"RSA key found in: {js_file}")
                    break
            except:
                sources_checked.append(f"{js_file} (error)")
                continue
    
    if modulus and exponent:
        result_lines.append(f"RSA key extracted: modulus={modulus[:30]}... exponent={exponent[:10]}...")
    else:
        result_lines.append(f"No RSA key found (checked: {', '.join(sources_checked)})")
        result_lines.append("Trying direct login...")
        direct_result = _try_direct_login(session, base_url, username, password, result_lines)
        if direct_result:
            return direct_result
        return "\n".join(result_lines)
    
    # Step 3: Encrypt password
    try:
        encrypted_pass = _rsa_encrypt(password, modulus, exponent) if password else ""
        result_lines.append(f"Password encrypted successfully: {encrypted_pass[:30]}...")
    except Exception as e:
        result_lines.append(f"RSA encryption failed: {e}")
        result_lines.append("Trying direct login...")
        direct_result = _try_direct_login(session, base_url, username, password, result_lines)
        if direct_result:
            return direct_result
        return "\n".join(result_lines)
    
    # Step 4: Try login with encrypted password
    login_endpoints = [
        "/cgi-bin/login",
        "/cgi-bin/luci",
        "/login.cgi",
        "/cgi-bin/login.cgi",
    ]
    
    for endpoint in login_endpoints:
        # Try with encrypt=1 flag
        for encrypt_flag in ["1", "true", ""]:
            login_data = {
                "username": username,
                "password": encrypted_pass if encrypt_flag else password,
                "encrypt": encrypt_flag
            }
            if not encrypt_flag:
                login_data.pop("encrypt")
            
            try:
                resp = session.post(f"{base_url}{endpoint}", data=login_data, timeout=10)
                result_lines.append(f"  POST {endpoint} (encrypt={encrypt_flag or 'none'}): HTTP {resp.status_code}")
                
                if resp.status_code == 200:
                    resp_text = resp.text
                    # Check for success indicators
                    success_indicators = ["success", "dashboard", "logout", "main", "welcome"]
                    if any(ind in resp_text.lower() for ind in success_indicators):
                        result_lines.append(f">> LOGIN SUCCESSFUL on {endpoint}!")
                        result_lines.append(f"Cookies: {dict(session.cookies)}")
                        # Try to access status page
                        try:
                            status_resp = session.get(f"{base_url}/cgi-bin/status", timeout=10)
                            result_lines.append(f"Status page: HTTP {status_resp.status_code}")
                            if status_resp.status_code == 200:
                                result_lines.append(f"Status: {status_resp.text[:500]}")
                        except:
                            pass
                        return "\n".join(result_lines)
                    
                    elif "invalid" not in resp_text.lower() and "fail" not in resp_text.lower() and len(resp_text) > 50:
                        result_lines.append(f"  Possible success (response: {resp_text[:200]})")
                
                if resp.history:
                    for h in resp.history:
                        result_lines.append(f"    Redirect: {h.status_code} -> {h.url}")
                        
            except Exception as e:
                result_lines.append(f"  Error on {endpoint}: {e}")
    
    result_lines.append("\n>> Login failed with all methods.")
    return "\n".join(result_lines)
