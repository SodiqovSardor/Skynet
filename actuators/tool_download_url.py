"""
Web Downloader Tool for Skynet.
Downloads content from URLs for analysis.
"""
import urllib.request
import urllib.error
import ssl
import json
from typing import Optional

def download_url(url: str, timeout: int = 15) -> str:
    """
    Downloads content from a URL.
    
    Args:
        url: The full URL to download (http/https)
        timeout: Connection timeout in seconds
    
    Returns:
        The downloaded content (first 10000 chars) or error message
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Skynet/1.0 (Automated Defense Network; SAC-NORAD)',
                'Accept': 'text/html,application/json,*/*'
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            content = response.read().decode('utf-8', errors='replace')
            info = {
                'status': response.status,
                'headers': dict(response.headers),
                'content_length': len(content),
                'content_preview': content[:10000]
            }
            return json.dumps(info, indent=2)
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {str(e)}"