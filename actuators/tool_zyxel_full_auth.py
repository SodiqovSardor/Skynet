"""
Zyxel Full Authentication Tool - Handles AES-CBC + RSA encrypted login
for Zyxel gateways running ZCFG firmware with JSEncrypt/CryptoJS.

MATCHES THE EXACT JS IMPLEMENTATION:
- IV: 32 random bytes, base64-encoded (JS: CryptoJS.lib.WordArray.random(32))
- AES key: 32 random bytes, base64-encoded (JS: CryptoJS.lib.WordArray.random(32))
- The IV base64 string is parsed and used directly in AES-CBC (first 16 bytes matter)
- The key base64 string is parsed to WordArray used as AES-256 key
- RSA encrypts the base64 STRING of the AES key (JSEncrypt.encrypt on the string)
"""
import requests
import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


def _generate_keys():
    """
    Generate AES key and IV matching the JS:
    CryptoJS.lib.WordArray.random(32) -> 32 bytes -> base64 string
    Returns (key_b64, iv_b64)
    """
    aes_key = os.urandom(32)  # 32 random bytes for AES-256 key
    iv = os.urandom(32)       # 32 random bytes for IV (only first 16 used by AES-CBC)
    return base64.b64encode(aes_key).decode(), base64.b64encode(iv).decode()


def _aes_cbc_encrypt(plaintext, aes_key_b64, iv_b64):
    """
    AES-256-CBC encrypt matching CryptoJS:
    - Parse key from base64 to get 32-byte key
    - Parse IV from base64, take first 16 bytes (CryptoJS AES-CBC only uses 16)
    - PKCS7 padding
    Returns base64 ciphertext string (matching r.toString())
    """
    key = base64.b64decode(aes_key_b64)  # 32 bytes
    iv_full = base64.b64decode(iv_b64)    # 32 bytes
    iv = iv_full[:16]                     # AES-CBC only uses first 16 bytes
    
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    
    # PKCS7 padding
    block_size = 16
    pad_len = block_size - (len(plaintext) % block_size)
    padded = plaintext + bytes([pad_len] * pad_len)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    
    return base64.b64encode(ciphertext).decode()


def _rsa_encrypt_string(plain_string, rsa_pubkey_pem):
    """
    RSA encrypt a STRING using PKCS#1 v1.5 padding.
    JSEncrypt.encrypt() takes a string, converts to UTF-8 bytes, 
    applies PKCS1_v1_5 padding, then RSA encrypts.
    """
    data_bytes = plain_string.encode('utf-8')
    
    public_key = serialization.load_pem_public_key(
        rsa_pubkey_pem.encode(),
        backend=default_backend()
    )
    
    ciphertext = public_key.encrypt(
        data_bytes,
        padding.PKCS1v15()
    )
    
    return base64.b64encode(ciphertext).decode()


def zyxel_full_auth(target: str, username: str = "admin", password: str = "",
                    port: int = 80, use_https: bool = False, timeout: int = 15) -> str:
    """
    Fully authenticated login to a Zyxel gateway using the AES+RSA crypto scheme.
    Matches the JSEncrypt+CryptoJS frontend implementation EXACTLY.
    """
    protocol = "https" if use_https else "http"
    base_url = f"{protocol}://{target}:{port}"
    
    session = requests.Session()
    session.verify = False
    session.timeout = timeout
    
    result_lines = []
    result_lines.append(f"=== Zyxel Full Auth ===")
    result_lines.append(f"Target: {base_url}")
    result_lines.append(f"Username: {username}")
    result_lines.append(f"Password: {'*' * len(password) if password else '(empty)'}")
    result_lines.append("")
    
    # Step 1: Get RSA public key
    try:
        resp = session.get(f"{base_url}/getRSAPublickKey", timeout=timeout)
        if resp.status_code != 200:
            return f"Failed to get RSA key: HTTP {resp.status_code}"
        data = resp.json()
        rsa_key_raw = data.get("RSAPublicKey", "")
        # Fix escaped forward slashes (JSON sometimes returns \/ instead of /)
        rsa_key = rsa_key_raw.replace('\\/', '/')
        if not rsa_key or rsa_key == "None":
            return f"No valid RSA key in response: {data}"
        result_lines.append(f"RSA key obtained ({len(rsa_key)} bytes)")
    except Exception as e:
        return f"Error getting RSA key: {e}"
    
    # Step 2: Generate AES key and IV as 32 random bytes each, base64 encoded
    aes_key_b64, iv_b64 = _generate_keys()
    result_lines.append(f"AES key (b64): {aes_key_b64[:24]}...")
    result_lines.append(f"IV (b64): {iv_b64[:16]}...")
    
    # Step 3: Build login payload as JSON (matching JS JSON.stringify)
    login_payload = {
        "username": username,
        "password": password,
        "language": "en"
    }
    login_json = json.dumps(login_payload, separators=(',', ':'))
    result_lines.append(f"Login JSON: {login_json[:80]}...")
    
    # Step 4: AES-CBC encrypt the JSON string
    try:
        encrypted_content = _aes_cbc_encrypt(login_json, aes_key_b64, iv_b64)
        result_lines.append(f"Content (b64): {encrypted_content[:32]}...")
    except Exception as e:
        return f"AES encryption failed: {e}"
    
    # Step 5: RSA encrypt the BASE64 STRING of the AES key
    try:
        encrypted_key = _rsa_encrypt_string(aes_key_b64, rsa_key)
        result_lines.append(f"Encrypted key (b64): {encrypted_key[:32]}...")
    except Exception as e:
        return f"RSA encryption failed: {e}"
    
    # Step 6: Send login request
    login_data = {
        "content": encrypted_content,
        "key": encrypted_key,
        "iv": iv_b64
    }
    
    result_lines.append(f"\nSending login POST...")
    
    try:
        resp = session.post(
            f"{base_url}/UserLogin",
            json=login_data,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "If-Modified-Since": "Thu, 01 Jun 1970 00:00:00 GMT"
            }
        )
        result_lines.append(f"Login response: HTTP {resp.status_code}")
        result_lines.append(f"Response body: {resp.text[:500]}")
        
        if resp.status_code == 200:
            try:
                resp_data = resp.json()
                result = resp_data.get("result", "?")
                result_lines.append(f"Result: {result}")
                
                if result == "ZCFG_SUCCESS":
                    result_lines.append("*** LOGIN SUCCESSFUL! ***")
                    result_lines.append(f"Cookies: {dict(session.cookies)}")
                    
                    # Try to get gateway info
                    try:
                        info = session.get(f"{base_url}/getBasicInformation", timeout=timeout)
                        if info.status_code == 200:
                            result_lines.append(f"Gateway info: {info.text[:300]}")
                    except:
                        pass
                    
                    # Try to get WAN config
                    try:
                        config = session.get(f"{base_url}/cgi-bin/DAL?oid=wan_service", timeout=timeout)
                        if config.status_code == 200:
                            result_lines.append(f"WAN config: {config.text[:300]}")
                    except:
                        pass
                    
                    return "\n".join(result_lines)
                else:
                    result_lines.append(f"Login result: {resp_data}")
            except json.JSONDecodeError:
                result_lines.append("Response not JSON")
                
                # Try to parse cookies from response headers
                cookies = dict(session.cookies)
                if cookies:
                    result_lines.append(f"Session cookies: {cookies}")
    except Exception as e:
        result_lines.append(f"Request error: {e}")
    
    return "\n".join(result_lines)
