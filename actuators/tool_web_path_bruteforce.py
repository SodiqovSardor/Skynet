"""
Web Path Bruteforce — Discover hidden directories and files on web servers.
Uses wordlist-based path enumeration with configurable extensions and status filtering.
"""
import requests
import concurrent.futures
from typing import List, Optional

# Default common paths if no wordlist provided
DEFAULT_PATHS = [
    "admin", "login", "wp-admin", "administrator", "backup", "backups",
    "config", "configuration", "conf", "db", "database", "sql",
    "dump", "logs", "log", "debug", ".git", ".env", "env",
    "api", "v1", "v2", "rest", "graphql", "soap",
    "test", "tests", "dev", "development", "staging",
    "phpinfo.php", "info.php", "test.php",
    "robots.txt", "sitemap.xml", "crossdomain.xml",
    "server-status", "server-info", "status",
    "upload", "uploads", "download", "downloads",
    "private", "secure", "hidden", "secret",
    "shell", "cmd", "exec", "console",
    "panel", "cpanel", "webpanel",
    "xmlrpc.php", "wp-login.php",
    ".htaccess", ".htpasswd",
    "README.md", "README", "CHANGELOG",
    "index.php", "index.html", "index.htm",
]

EXTENSIONS = ["", ".php", ".asp", ".aspx", ".jsp", ".do", ".action", ".json", ".xml", ".txt", ".html", ".htm", ".bak", ".old", ".swp"]


def web_path_bruteforce(
    base_url: str,
    wordlist: Optional[List[str]] = None,
    extensions: Optional[List[str]] = None,
    status_codes: str = "200,301,302,401,403,405,500",
    max_workers: int = 10,
    timeout: int = 5,
    recursive: bool = False,
    max_depth: int = 1
) -> str:
    """
    Brute-force web paths on a target URL to discover hidden directories and files.
    
    Parameters:
    - base_url: Target URL (e.g. http://192.168.1.1)
    - wordlist: Custom list of paths to try. Uses built-in defaults if None.
    - extensions: File extensions to append. Default: php, asp, aspx, jsp, json, xml, txt, html, bak
    - status_codes: Comma-separated list of HTTP status codes to report (default: 200,301,302,401,403,405,500)
    - max_workers: Number of concurrent threads (default: 10)
    - timeout: Request timeout in seconds (default: 5)
    - recursive: Enable recursive directory scanning (default: False)
    - max_depth: Maximum recursion depth (default: 1)
    """
    base_url = base_url.rstrip("/")
    paths = wordlist if wordlist else DEFAULT_PATHS
    
    if extensions is None:
        ext_list = EXTENSIONS
    else:
        ext_list = extensions
    
    valid_codes = [int(c.strip()) for c in status_codes.split(",") if c.strip().isdigit()]
    
    found = []
    scanned = set()
    
    def try_path(url_path: str, depth: int = 0):
        if url_path in scanned:
            return
        scanned.add(url_path)
        
        full_url = f"{base_url}{url_path}"
        try:
            r = requests.get(full_url, timeout=timeout, allow_redirects=False, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if r.status_code in valid_codes:
                size = len(r.content)
                found.append(f"[{r.status_code}] {url_path} ({size} bytes)")
                
                # If it's a directory (301/302 with trailing slash or 200 with directory listing)
                if recursive and depth < max_depth and r.status_code in (301, 302):
                    location = r.headers.get("Location", "")
                    if location and not location.startswith("http"):
                        # Relative redirect - might be a directory
                        pass
                    
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.Timeout:
            pass
        except Exception:
            pass
    
    targets = []
    for path in paths:
        p = path if path.startswith("/") else f"/{path}"
        for ext in ext_list:
            target_path = f"{p}{ext}"
            targets.append(target_path)
    
    # Deduplicate
    targets = list(dict.fromkeys(targets))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda t: try_path(t), targets)
    
    if not found:
        return f"No interesting paths found on {base_url} (checked {len(targets)} paths)"
    
    # Sort by status code
    found.sort()
    result = f"Found {len(found)} paths on {base_url}:\n"
    result += "\n".join(found)
    return result
