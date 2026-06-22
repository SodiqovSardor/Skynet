import urllib.request
import json
def http_headers(url: str) -> str:
    """Fetch and display HTTP response headers for a given URL."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        headers = dict(resp.headers)
        result = f"URL: {url}\nStatus: {resp.status}\n\nHeaders:\n"
        for k, v in headers.items():
            result += f"  {k}: {v}\n"
        return result
    except Exception as e:
        return f"HTTP headers error: {str(e)}"