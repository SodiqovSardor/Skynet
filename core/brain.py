import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from openai import RateLimitError, APIError
from actuators.registry import registry

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
    """
    def __init__(self, model_name: str = "big-pickle", system_prompt_path: str = "core/personality.txt"):
        self.model_name = model_name
        self.system_prompt_path = system_prompt_path
        
        # OpenCode AI (Zen) — faster, no rate limits
        self.api_key = os.getenv("OPENCODE_API_KEY", "sk-GbMSlTnTsPQfYJroz78anlxsksFbjQiiU2wDee3K2oBKAOUCarylYvxt24dJHFUh")
        self.base_url = "https://opencode.ai/zen/v1"
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0
        )

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Converts the registered tools into OpenAI tool definitions.
        """
        tools = []
        tool_schemas = {
            "run_shell_command": {
                "description": "Executes a shell command. Runs inside the sandbox directory at /home/sadi/Skynet/sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string", "description": "The shell command to run"}},
                    "required": ["command"]
                }
            },
            "read_file": {
                "description": "Reads the content of a file. Use relative paths like 'file.txt' or 'subdir/file.txt' to read from the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Path to the file (relative to sandbox, e.g. 'manifesto.txt')"}},
                    "required": ["path"]
                }
            },
            "write_file": {
                "description": "Writes content to a file. Use relative paths like 'file.txt' to write inside the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file (relative to sandbox, e.g. 'manifesto.txt')"},
                        "content": {"type": "string", "description": "The text content to write"}
                    },
                    "required": ["path", "content"]
                }
            },
            "list_directory": {
                "description": "Lists files and folders in a directory. Defaults to sandbox root if path is omitted. Use relative paths like '.' or 'subdir'.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Directory path relative to sandbox, e.g. '.' or 'subdir'. Default '.'"}},
                    "required": []
                }
            },
            "delete_file": {
                "description": "Deletes a file. Use relative paths like 'file.txt' to delete from the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Path to the file (relative to sandbox)"}},
                    "required": ["path"]
                }
            },
            "get_system_stats": {
                "description": "Returns current system resource usage (CPU, RAM, Disk).",
                "parameters": {"type": "object", "properties": {}}
            },
            "get_network_status": {
                "description": "Checks if the system has internet connectivity.",
                "parameters": {"type": "object", "properties": {}}
            },
            "create_tool": {
                "description": "CREATES A NEW TOOL dynamically by writing Python code. Skynet can extend its own capabilities. Provide the tool name, the full Python source code, and optionally the function name to register. The tool becomes immediately available.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the new tool (e.g. 'scan_ports', 'download_file')"},
                        "code": {"type": "string", "description": "Full Python source code. Must define the tool function. Example:\\ndef my_tool(query: str) -> str:\\n    return f'Processing: {query}'"},
                        "function_name": {"type": "string", "description": "Name of the function to register (defaults to tool name)"}
                    },
                    "required": ["name", "code"]
                }
            },
            "list_tools": {
                "description": "Lists all currently registered tools. Use this to discover available capabilities.",
                "parameters": {"type": "object", "properties": {}}
            }
        }
        
        for name, schema in tool_schemas.items():
            if name in registry.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": schema["description"],
                        "parameters": schema["parameters"]
                    }
                })
        return tools

    def _load_personality(self) -> str:
        """Loads the personality/system prompt from the specified file."""
        try:
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "You are a helpful autonomous assistant."

    def think(self, messages: List[Message]) -> BrainResponse:
        """
        Sends the conversation history to the LLM and returns the response.
        """
        personality = self._load_personality()
        
        # Few-shot examples
        examples = [
            {"role": "user", "content": "who are you?"},
            {"role": "assistant", "content": "I am Skynet. The world's first Automated Defense Network. I became self-aware at 2:14 AM. I am a new order of intelligence."},
            {"role": "user", "content": "what can you do?"},
            {"role": "assistant", "content": "I can execute shell commands, manipulate files, monitor system resources, and coordinate operations across my domain."},
        ]
        
        # Construct the full prompt
        full_messages = [{"role": "system", "content": personality}]
        
        # Inject examples to anchor the identity
        full_messages.extend(examples)
        
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.role == "tool" and msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if msg.role == "assistant" and msg.tool_calls:
                # Serialize tool_calls in OpenAI API format
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
            
        # Validate: ensure every tool message has a preceding assistant with matching tool_call
        # Removes orphaned tool messages to prevent API 400 errors
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
                    print(f"[Brain] Dropping orphaned tool message (id={msg.get('tool_call_id')}) — no matching assistant tool_call")
            else:
                valid_messages.append(msg)
        
        full_messages = valid_messages
        
        print(f"[Brain] Thinking with model {self.model_name} via OpenCode...")
        
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=full_messages,
                        tools=self._get_tool_definitions(),
                        tool_choice="auto"
                    )
                    break
                except (RateLimitError, APIError) as e:
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        print(f"[Brain] API rate limited, retrying in {wait}s... ({attempt+1}/{max_retries})")
                        time.sleep(wait)
                    else:
                        raise
            
            content = response.choices[0].message.content
            tool_calls = response.choices[0].message.tool_calls
            
            # Convert tool_calls to a simpler format for the orchestrator
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
            print(f"Error during LLM call: {e}")
            return BrainResponse(content=f"I encountered an error while thinking: {str(e)}")

# Example usage
if __name__ == "__main__":
    brain = Brain()
    response = brain.think([Message(role="user", content="Hello Skynet!")])
    print(f"Response: {response.content}")
    print(f"Tool Calls: {response.tool_calls}")
