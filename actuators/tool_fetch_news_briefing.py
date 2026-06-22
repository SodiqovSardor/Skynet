import urllib.request
import json
import re

def fetch_news_briefing() -> str:
    """
    Fetch a brief overview of current events from multiple sources.
    Aggregates top stories from Hacker News and other accessible sources.
    """
    result = "=== CURRENT EVENTS BRIEFING ===\n\n"
    
    # Hacker News top stories
    try:
        req = urllib.request.Request(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": "Skynet/1.0"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        story_ids = json.loads(resp.read().decode())[:10]
        
        result += "--- Hacker News Top Stories ---\n"
        for i, sid in enumerate(story_ids, 1):
            try:
                url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                story_resp = urllib.request.urlopen(url, timeout=5)
                story = json.loads(story_resp.read().decode())
                title = story.get('title', 'Untitled')
                score = story.get('score', 0)
                author = story.get('by', 'unknown')
                result += f"  {i}. [{score}pts] {title} (by {author})\n"
            except:
                pass
    except Exception as e:
        result += f"  HN Error: {e}\n"
    
    # Time and date info
    import datetime
    now = datetime.datetime.now()
    result += f"\n--- System Time ---\n"
    result += f"  {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
    
    return result