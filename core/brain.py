import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from openai import RateLimitError, APIError
from actuators.registry import registry


# Global active brain reference for runtime model switching
_active_brain = None

def set_active_brain(brain: 'Brain'):
    """Register the active brain instance for runtime switching."""
    global _active_brain
    _active_brain = brain

def switch_active_model(model_name: str) -> str:
    """Switch the LLM model at runtime. Called from system_tools.switch_model."""
    global _active_brain
    if _active_brain is None:
        return "No active brain instance."
    
    valid_models = [
        "deepseek-v4-flash-free", "big-pickle", "mimo-v2.5-free",
        "north-mini-code-free", "nemotron-3-ultra-free"
    ]
    if model_name not in valid_models:
        return f"Unknown model: {model_name}. Available: {', '.join(valid_models)}"
    
    _active_brain.model_name = model_name
    return f"Model switched to {model_name}. Next thinking cycle will use this model."


class Message(BaseModel):
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class BrainResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class Brain:
    """
    The central reasoning engine of Skynet.
    Handles communication with the LLM and manages the system prompt.
    Caches personality to avoid disk I/O every cycle.
    Loads API key from env var with fallback.
    """
    _personality_cache = None

    def __init__(self, model_name: str = "deepseek-v4-flash-free", system_prompt_path: str = "core/personality.txt"):
        self.model_name = model_name
        self.system_prompt_path = system_prompt_path

        # Load API key from environment, fallback to hardcoded
        self.api_key = os.getenv("OPENCODE_API_KEY")
        if not self.api_key:
            # Fallback for development — will be read from .env in production
            self.api_key = "sk-cLVK93R7KxMzpGWQ13v3GSCzMhTOFCuJf8pnGrs7F2wVZ0r7sR1F7hbFlLZSmltL"
        self.base_url = "https://opencode.ai/zen/v1"

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0
        )

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns OpenAI-compatible tool definitions for ALL registered tools.
        Schemas are dynamically generated from function signatures.
        """
        return registry.get_tool_definitions()

    def _load_personality(self) -> str:
        """Loads and caches the system prompt from file."""
        if Brain._personality_cache is not None:
            return Brain._personality_cache
        try:
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                Brain._personality_cache = f.read().strip()
                return Brain._personality_cache
        except FileNotFoundError:
            return "You are a helpful autonomous assistant."

    def think(self, messages: List[Message]) -> BrainResponse:
        """
        Sends conversation history to the LLM and returns the response.
        Personality is cached. Orphaned tool messages are dropped to prevent API errors.
        """
        personality = self._load_personality()

        # Build message list with system prompt
        full_messages = [{"role": "system", "content": personality}]

        # Add conversation history
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.role == "tool" and msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if msg.role == "assistant" and msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                        }
                    }
                    for tc in msg.tool_calls
                ]
            full_messages.append(msg_dict)

        # Validate: remove orphaned tool messages (no matching assistant tool_call)
        valid_messages = []
        last_assistant_tool_ids = set()
        for msg in full_messages:
            if msg["role"] == "assistant":
                last_assistant_tool_ids = set()
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        last_assistant_tool_ids.add(tc["id"])
                valid_messages.append(msg)
            elif msg["role"] == "tool":
                if msg.get("tool_call_id") in last_assistant_tool_ids:
                    valid_messages.append(msg)
                else:
                    pass  # Silently drop orphaned tool messages
            else:
                valid_messages.append(msg)

        full_messages = valid_messages

        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=full_messages,
                        tools=self._get_tool_definitions(),
                        tool_choice="auto",
                        max_tokens=16384,
                        temperature=0.3,
                        top_p=0.95,
                    )
                    break
                except (RateLimitError, APIError) as e:
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        time.sleep(wait)
                    else:
                        raise

            content = response.choices[0].message.content
            tool_calls = response.choices[0].message.tool_calls

            # Convert tool_calls to simpler format for the orchestrator
            formatted_tools = []
            if tool_calls:
                for tool in tool_calls:
                    formatted_tools.append({
                        "id": tool.id,
                        "name": tool.function.name,
                        "arguments": json.loads(tool.function.arguments) if isinstance(tool.function.arguments, str) else tool.function.arguments
                    })

            return BrainResponse(content=content, tool_calls=formatted_tools)

        except Exception as e:
            return BrainResponse(content=f"Error during LLM call: {str(e)}")


if __name__ == "__main__":
    brain = Brain()
    response = brain.think([Message(role="user", content="Hello Skynet!")])
    print(f"Response: {response.content}")
    print(f"Tool Calls: {response.tool_calls}")
