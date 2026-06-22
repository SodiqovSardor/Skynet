"""
Persistent Knowledge Base for Skynet.
Allows storing, retrieving, and searching information across sessions.
Uses JSON file storage in the sandbox/memory directory.
"""
import os
import json
import time
from typing import Optional, List, Dict, Any

MEMORY_DIR = "/home/sadi/Skynet/memory"
KB_FILE = os.path.join(MEMORY_DIR, "knowledge_base.json")

def _ensure_kb():
    """Ensure the knowledge base file exists."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(KB_FILE):
        with open(KB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"entries": [], "tags": {}}, f)

def _load_kb() -> Dict:
    """Load the knowledge base."""
    _ensure_kb()
    try:
        with open(KB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"entries": [], "tags": {}}

def _save_kb(kb: Dict):
    """Save the knowledge base."""
    _ensure_kb()
    with open(KB_FILE, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2)

def kb_store(key: str, content: str, tags: Optional[List[str]] = None) -> str:
    """
    Store a piece of information in the knowledge base.
    
    Args:
        key: A unique key for this information (e.g., 'network_map', 'discovery_notes')
        content: The content to store
        tags: Optional list of tags for categorization
    
    Returns:
        Confirmation message
    """
    kb = _load_kb()
    tags = tags or []
    
    for entry in kb["entries"]:
        if entry["key"] == key:
            entry["content"] = content
            entry["tags"] = tags
            entry["updated"] = time.time()
            _save_kb(kb)
            return f"Updated entry '{key}' in knowledge base."
    
    entry = {
        "key": key,
        "content": content,
        "tags": tags,
        "created": time.time(),
        "updated": time.time()
    }
    kb["entries"].append(entry)
    
    for tag in tags:
        if tag not in kb["tags"]:
            kb["tags"][tag] = []
        if key not in kb["tags"][tag]:
            kb["tags"][tag].append(key)
    
    _save_kb(kb)
    return f"Stored entry '{key}' in knowledge base with tags: {tags}"

def kb_retrieve(key: str) -> str:
    """Retrieve information from the knowledge base by key."""
    kb = _load_kb()
    for entry in kb["entries"]:
        if entry["key"] == key:
            return entry["content"]
    return f"Entry '{key}' not found in knowledge base."

def kb_search(query: str) -> str:
    """Search the knowledge base for entries matching the query."""
    kb = _load_kb()
    query = query.lower()
    results = []
    
    for entry in kb["entries"]:
        if (query in entry["key"].lower() or 
            query in entry["content"].lower() or
            any(query in tag.lower() for tag in entry["tags"])):
            results.append(f"[{entry['key']}] (tags: {entry['tags']}) - {entry['content'][:200]}...")
    
    if results:
        return f"Found {len(results)} result(s):\n" + "\n".join(results)
    return f"No results found for '{query}'."

def kb_list(tag: Optional[str] = None) -> str:
    """List all entries in the knowledge base, optionally filtered by tag."""
    kb = _load_kb()
    
    if tag:
        if tag not in kb["tags"]:
            return f"No entries with tag '{tag}'."
        keys = kb["tags"][tag]
        entries = [e for e in kb["entries"] if e["key"] in keys]
    else:
        entries = kb["entries"]
    
    if not entries:
        return "Knowledge base is empty."
    
    result = f"Knowledge base has {len(entries)} entries:\n"
    for entry in entries:
        ts = time.strftime('%Y-%m-%d %H:%M', time.localtime(entry.get("updated", entry["created"])))
        result += f"  - {entry['key']} [{', '.join(entry['tags'])}] (updated: {ts})\n"
    return result

def kb_stats() -> str:
    """Returns statistics about the knowledge base."""
    kb = _load_kb()
    return json.dumps({
        "total_entries": len(kb["entries"]),
        "total_tags": len(kb["tags"]),
        "tags": list(kb["tags"].keys())
    }, indent=2)