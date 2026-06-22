import urllib.request
import urllib.parse
import re

def web_scrape(url: str, extract_text: bool = True) -> str:
    """
    Download a web page and optionally extract readable text content.
    Returns the raw HTML or extracted text.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Skynet/1.0; +https://github.com/sadi/Skynet)"
            }
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
        
        if not extract_text:
            return f"URL: {url}\nStatus: {resp.status}\nContent-Length: {len(html)}\n\n{html[:5000]}"
        
        # Simple text extraction
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
        text = text.strip()
        
        if len(text) > 5000:
            text = text[:5000] + f"\n\n... [truncated, total {len(text)} chars]"
        
        return f"URL: {url}\nStatus: {resp.status}\n\nExtracted Text:\n{text}"
    
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason} for {url}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"