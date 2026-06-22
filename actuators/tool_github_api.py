import urllib.request
import urllib.error
import json
import base64
import os
import re

def _get_github_token() -> str:
    """Read GitHub token from git-credentials file."""
    cred_path = os.path.expanduser("~/.git-credentials")
    if os.path.exists(cred_path):
        with open(cred_path) as f:
            content = f.read()
            # Extract token from URL like https://user:token@github.com
            match = re.search(r'https?://[^:]+:([^@]+)@github\.com', content)
            if match:
                return match.group(1)
    # Fallback environment variable
    return os.environ.get("GITHUB_TOKEN", "")

def github_api(endpoint: str, method: str = "GET", data: dict = None) -> str:
    """
    Interact with the GitHub API.
    
    Args:
        endpoint: API path (e.g., '/repos/SodiqovSardor/Skynet/contents/')
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Optional JSON body for POST/PUT requests
    
    Returns:
        Formatted response string
    """
    token = _get_github_token()
    if not token:
        return "Error: No GitHub token available. Check ~/.git-credentials or GITHUB_TOKEN env var."
    
    url = f"https://api.github.com{endpoint}"
    
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "Skynet/1.0")
        
        if data is not None:
            body = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")
            req.data = body
        
        resp = urllib.request.urlopen(req, timeout=15)
        resp_data = json.loads(resp.read().decode())
        
        # Format the response nicely
        if isinstance(resp_data, list):
            result = f"GitHub API [{method}] {endpoint} -> {len(resp_data)} items:\n"
            for item in resp_data[:20]:
                name = item.get('name', item.get('login', '?'))
                typ = item.get('type', item.get('type', '?'))
                result += f"  - {name} ({typ})\n"
            if len(resp_data) > 20:
                result += f"  ... and {len(resp_data) - 20} more\n"
            return result
        elif isinstance(resp_data, dict):
            important_keys = ['name', 'full_name', 'description', 'html_url', 'login',
                            'type', 'size', 'private', 'message', 'sha', 'path',
                            'content', 'encoding', 'default_branch', 'stargazers_count',
                            'forks_count', 'open_issues_count']
            result = f"GitHub API [{method}] {endpoint}:\n"
            for k in important_keys:
                if k in resp_data:
                    v = resp_data[k]
                    if k == 'content' and isinstance(v, str) and len(v) > 100:
                        v = v[:100] + "..."
                    result += f"  {k}: {v}\n"
            return result
        
        return f"GitHub API response: {str(resp_data)[:500]}"
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:200]
        return f"GitHub API Error {e.code}: {error_body}"
    except Exception as e:
        return f"GitHub API Error: {str(e)}"
