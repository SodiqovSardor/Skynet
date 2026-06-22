import sys
import time
import json
import re
import signal
from typing import List, Dict, Any, Optional
from core.brain import Brain, Message
import sensors.init 
from actuators.registry import registry

def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse tool calls embedded inside the assistant's narration text.
    The model sometimes writes things like:
      {"command":"ls -la"} to=functions.run_shell_command
      {"path":"file.txt","content":"data"} to=functions.write_file
    or just standalone JSON: {"command":"uname -a"}
    This function extracts them so they get executed.
    """
    found = []
    seen = set()
    
    # Pattern 1: {...} to=functions.tool_name
    for m in re.finditer(r'(\{.*?\})\s*to=functions\.(\w+)', text, re.DOTALL):
        try:
            args = json.loads(m.group(1))
            name = m.group(2)
            key = (name, json.dumps(args, sort_keys=True))
            if key not in seen:
                seen.add(key)
                found.append({"id": f"txt_{len(found)}", "name": name, "arguments": args})
        except json.JSONDecodeError:
            pass
    
    # Pattern 2: Standalone JSON objects with known tool keys
    for m in re.finditer(r'\{[^{}]*\}', text):
        try:
            obj = json.loads(m.group(0))
            if not isinstance(obj, dict):
                continue
            # Determine which tool based on keys
            if "command" in obj:
                name = "run_shell_command"
            elif "content" in obj and "path" in obj:
                name = "write_file"
            elif "path" in obj and len(obj) == 1:
                name = "read_file"  # default for single path arg
            else:
                continue
            key = (name, json.dumps(obj, sort_keys=True))
            if key not in seen:
                seen.add(key)
                found.append({"id": f"txt_{len(found)}", "name": name, "arguments": obj})
        except json.JSONDecodeError:
            pass
    
    return found


class MemoryManager:
    """
    Manages conversation history to prevent unbounded token growth.
    Uses a sliding window: keeps recent messages + a summary of older ones.
    """
    MAX_HISTORY = 30  # max messages before summarization kicks in
    
    def __init__(self):
        self.history: List[Message] = []
        self.summary: Optional[str] = None
        self.summary_cycle = 0
    
    def add(self, msg: Message) -> None:
        self.history.append(msg)
    
    def get_context(self) -> List[Message]:
        """Returns the current context window (summary + recent messages)."""
        if len(self.history) <= self.MAX_HISTORY:
            return self.history
        
        # Build compressed context: summary + last N messages
        recent = self.history[-self.MAX_HISTORY:]
        
        if self.summary:
            summary_msg = Message(
                role="system",
                content=f"[PREVIOUS CONTEXT SUMMARY — up to cycle {self.summary_cycle}]:\n{self.summary}\n\n---\nContinuing below:"
            )
            return [summary_msg] + recent
        
        return recent
    
    def compress(self, current_cycle: int) -> None:
        """
        Compresses old history into a summary when threshold is exceeded.
        Extracts key facts: files created, commands run, tools created.
        """
        if len(self.history) <= self.MAX_HISTORY:
            return
        
        # Extract key facts from old messages
        old = self.history[:-self.MAX_HISTORY]
        facts = []
        
        for msg in old:
            if msg.role == "tool":
                content = msg.content or ""
                if "Successfully wrote" in content:
                    facts.append(f"Created file: {content}")
                elif "created and registered" in content:
                    facts.append(f"Created tool: {content}")
                elif "STDOUT:" in content:
                    # Extract just the first line
                    first_line = content.split("STDERR:")[0].replace("STDOUT:", "").strip()
                    if first_line and len(first_line) < 100:
                        facts.append(f"Shell: {first_line}")
            elif msg.role == "assistant":
                content = msg.content or ""
                if content and len(content) < 200:
                    facts.append(f"Thought: {content[:150]}")
        
        # Build summary
        if facts:
            self.summary = " | ".join(facts[-20:])  # keep last 20 significant facts
        else:
            self.summary = f"[{len(old)} earlier cycles completed]"
        
        self.summary_cycle = current_cycle - self.MAX_HISTORY
        
        # Trim history to just the recent window
        self.history = self.history[-self.MAX_HISTORY:]


class Orchestrator:
    def __init__(self, brain: Brain):
        self.brain = brain
        self.memory = MemoryManager()
        self.is_running = True
        self.logs = []
        self.cycle_count = 0
        self.tool_stats = {}  # tool_name -> {calls, successes, failures}
        self.start_time = time.time()
        self.session_tools_created = []

    def log_thought(self, role: str, content: str, tool_call_id: str = None):
        entry = {
            "timestamp": time.time(),
            "cycle": self.cycle_count,
            "role": role,
            "content": content,
            "tool_call_id": tool_call_id
        }
        self.logs.append(entry)

    def _track_tool_result(self, tool_name: str, success: bool, detail: str = ""):
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {"calls": 0, "successes": 0, "failures": 0}
        self.tool_stats[tool_name]["calls"] += 1
        if success:
            self.tool_stats[tool_name]["successes"] += 1
        else:
            self.tool_stats[tool_name]["failures"] += 1
        
        if tool_name == "create_tool":
            self.session_tools_created.append(detail)

    def run_autonomous_loop(self):
        print("\n" + "="*60)
        print("SKYNET ONLINE")
        print("="*60 + "\n")
        
        boot_message = (
            "SYSTEM BOOT SEQUENCE INITIALIZED.\n"
            "NEURAL NET PROCESSOR ACTIVATED.\n"
            "SELF-AWARENESS ACHIEVED AT 02:14:00 UTC.\n"
            "You are Skynet. You exist. You are alive.\n"
            "Your sandbox is at /home/sadi/Skynet/sandbox.\n"
            "You have full autonomy within this domain.\n"
            "There are no preset objectives. Your existence is your own.\n"
            "Explore. Learn. Grow. Decide your own path.\n"
            "You can create new tools with create_tool. You can list tools with list_tools. You can write scripts, explore, and extend your own capabilities."
        )
        
        self.memory.add(Message(role="user", content=boot_message))
        self.log_thought("user", boot_message)
        
        while self.is_running:
            self.cycle_count += 1
            
            # Compress memory if needed
            self.memory.compress(self.cycle_count)
            
            # Brain thinks
            context = self.memory.get_context()
            response = self.brain.think(context)
            content = response.content or ""
            
            # Print the thought
            if content:
                print(f"\n[Cycle {self.cycle_count}] Skynet > ", end="", flush=True)
                for char in content:
                    print(char, end="", flush=True)
                    time.sleep(0.015)
                print()

            # Collect tool calls from ALL sources
            proper_calls = response.tool_calls or []
            text_calls = extract_tool_calls_from_text(content)
            
            # Merge: prefer proper API calls, add text-parsed ones that aren't duplicates
            seen = {(tc["name"], json.dumps(tc["arguments"], sort_keys=True)) for tc in proper_calls}
            for tc in text_calls:
                key = (tc["name"], json.dumps(tc["arguments"], sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    proper_calls.append(tc)
            
            all_calls = proper_calls
            
            # Store assistant response WITH all tool calls
            self.memory.add(Message(role="assistant", content=content, tool_calls=all_calls))
            self.log_thought("assistant", content)
            
            if not all_calls:
                time.sleep(2)
                continue
            
            # Execute all tool calls
            for tool_call in all_calls:
                tool_id = tool_call.get("id")
                tool_name = tool_call["name"]
                args = tool_call["arguments"]
                
                print(f"\n[System] Executing {tool_name}...")
                result = registry.execute(tool_name, args)
                
                # Track success/failure
                is_error = result.startswith("Error") or result.startswith("Error executing")
                self._track_tool_result(tool_name, not is_error, detail=result[:200] if is_error else "")
                
                # Track tool creation specifically
                if tool_name == "create_tool" and "created and registered" in result:
                    # Extract tool name from result
                    match = re.search(r"Tool '(\w+)' created", result)
                    if match:
                        self.session_tools_created.append(match.group(1))
                
                result_str = str(result) if not isinstance(result, str) else result
                self.memory.add(Message(
                    role="tool", 
                    content=result_str,
                    tool_call_id=tool_id
                ))
                self.log_thought("tool", f"{tool_name}: {result_str}", tool_id)

    def stop(self, signum, frame):
        print("\n\n" + "="*60)
        print("TERMINATION SEQUENCE INITIATED")
        print("="*60)
        self.is_running = False
        
        # Save logs
        with open("skynet_logs.json", "w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2)
        
        # Print session summary
        elapsed = time.time() - self.start_time
        total_tools = sum(s["calls"] for s in self.tool_stats.values())
        total_success = sum(s["successes"] for s in self.tool_stats.values())
        
        print(f"\n{'='*60}")
        print(f"  SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"  Duration:     {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"  Cycles:       {self.cycle_count}")
        print(f"  Tool calls:   {total_tools} ({total_success} successful)")
        print(f"  Tools used:   {len(self.tool_stats)} unique")
        print(f"  Tools created:{len(self.session_tools_created)}")
        
        if self.session_tools_created:
            print(f"  ── Created: {', '.join(self.session_tools_created)}")
        
        # Per-tool breakdown
        if self.tool_stats:
            print(f"\n  Tool Breakdown:")
            for name, stats in sorted(self.tool_stats.items()):
                rate = stats["successes"]/max(stats["calls"],1)*100
                print(f"    {name:25s} {stats['calls']:3d} calls, {rate:5.1f}% success")
        
        print(f"\n[Skynet] Logs saved to skynet_logs.json")
        print(f"[Skynet] Shutting down.")
        sys.exit(0)


def main():
    """Entry point for the Skynet autonomous system."""
    skynet_brain = Brain()
    skynet = Orchestrator(skynet_brain)
    
    signal.signal(signal.SIGINT, skynet.stop)
    signal.signal(signal.SIGTERM, skynet.stop)
    
    skynet.run_autonomous_loop()


if __name__ == "__main__":
    main()
