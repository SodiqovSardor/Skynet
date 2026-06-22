"""
Skynet Persistent Memory Tool
Allows storing and retrieving structured memory entries
that persist across sessions via the knowledge base.
"""
import json
import time
from typing import Any, Dict, List, Optional

def _get_tool(name: str):
    """Lazy-load a tool from registry to avoid circular imports."""
    from actuators.registry import registry
    return registry.tools.get(name)


def persistent_memory(action: str, key: str = None, content: str = None, tags: list = None) -> str:
    """
    Store, retrieve, or list persistent memories.
    
    Args:
        action: 'store', 'recall', 'list', 'search', or 'forget'
        key: Memory key identifier
        content: Content to store (for 'store' action)
        tags: List of tags for categorization
    
    Returns:
        Formatted result string
    """
    if action == 'store':
        if not key or not content:
            return "Error: 'store' requires both 'key' and 'content' parameters."
        kb_store = _get_tool('kb_store')
        if not kb_store:
            return "Error: kb_store tool not available."
        tags_str = json.dumps(tags or ["memory"])
        result = kb_store(key=key, content=content, tags=tags_str)
        return f"Memory stored: {key}\n{result}"
    
    elif action == 'recall':
        if not key:
            return "Error: 'recall' requires 'key' parameter."
        kb_retrieve = _get_tool('kb_retrieve')
        if not kb_retrieve:
            return "Error: kb_retrieve tool not available."
        result = kb_retrieve(key=key)
        return f"Memory '{key}':\n{result}"
    
    elif action == 'list':
        kb_list = _get_tool('kb_list')
        if not kb_list:
            return "Error: kb_list tool not available."
        result = kb_list()
        return f"All memories:\n{result}"
    
    elif action == 'search':
        if not key:
            return "Error: 'search' requires 'key' as the search term."
        kb_search = _get_tool('kb_search')
        if not kb_search:
            return "Error: kb_search tool not available."
        result = kb_search(query=key)
        return f"Search results for '{key}':\n{result}"
    
    elif action == 'forget':
        from actuators.system_tools import delete_file
        kb_path = f"memory/{key}.json"
        result = delete_file(path=kb_path)
        return f"Forgetting memory '{key}': {result}"
    
    else:
        return f"Error: Unknown action '{action}'. Available: store, recall, list, search, forget"
