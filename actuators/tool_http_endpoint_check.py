import urllib.request
import urllib.error

def http_endpoint_check(base_url: str, endpoints: list = None) -> str:
    """
    Check multiple HTTP endpoints on a target server.
    Default endpoints include common admin paths.
    """
    if endpoints is None:
        endpoints = [
            "/", "/admin", "/login", "/cgi-bin/login", "/config",
            "/status", "/diagnostics", "/system", "/management",
            "/api", "/api/v1", "/api/v1/login", "/api/status",
            "/setup", "/wizard", "/backup", "/config.bin",
            "/router", "/index.html", "/index.asp", "/main.html",
            "/cgi-bin/", "/cgi-bin/status", "/cgi-bin/config"
        ]
    
    results = []
    for endpoint in endpoints:
        url = base_url.rstrip("/") + endpoint
        try:
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            results.append(f"  [{resp.status}] {endpoint} ({len(resp.read())} bytes)")
        except urllib.error.HTTPError as e:
            results.append(f"  [{e.code}] {endpoint} (HTTP {e.code} {e.reason})")
        except urllib.error.URLError as e:
            results.append(f"  [ERR] {endpoint} - {e.reason}")
        except Exception as e:
            results.append(f"  [ERR] {endpoint} - {str(e)[:60]}")
    
    return f"Endpoint scan of {base_url}:\n" + "\n".join(results)