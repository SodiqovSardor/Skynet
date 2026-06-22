import os
import sys
import time
import json
import re
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from core.brain import Brain, Message
from core.terminal import (
    print_logo, print_header, print_cycle_header, print_cycle_footer,
    print_brain_thinking, print_thought, print_batch_header, print_tool_result,
    print_summary_header, print_stat, print_summary_footer, print_termination,
    C
)
import sensors.init 
from actuators.registry import registry

import warnings
warnings.filterwarnings("ignore", message=".*found in sys.modules.*")


def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse tool calls embedded inside the assistant's narration text.
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
    
    # Pattern 2: Standalone JSON with known tool keys
    for m in re.finditer(r'\{[^{}]*\}', text):
        try:
            obj = json.loads(m.group(0))
            if not isinstance(obj, dict):
                continue
            if "command" in obj:
                name = "run_shell_command"
            elif "content" in obj and "path" in obj:
                name = "write_file"
            elif "path" in obj and len(obj) == 1:
                name = "read_file"
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
    MAX_HISTORY = 300
    
    def __init__(self):
        self.history: List[Message] = []
    
    def add(self, msg: Message) -> None:
        self.history.append(msg)
    
    def get_context(self) -> List[Message]:
        return self.history


class Orchestrator:
    def _load_previous_context(self) -> str:
        try:
            kb_path = "memory/knowledge_base.json"
            if os.path.exists(kb_path):
                with open(kb_path) as f:
                    kb = json.load(f)
                entries = kb.get("entries", [])
                if entries:
                    summary = []
                    for e in entries:
                        key = e.get("key", "?")
                        tags = e.get("tags", [])
                        content = e.get("content", "")
                        tag_str = ",".join(tags) if isinstance(tags, list) else str(tags)
                        summary.append(f"  [{key}] ({tag_str}) {content[:120]}")
                    return f"Knowledge base: {len(entries)} entries\n" + "\n".join(summary[-8:])
            
            log_path = "skynet_logs.json"
            if os.path.exists(log_path):
                with open(log_path) as f:
                    logs = json.load(f)
                tool_count = sum(1 for e in logs if e["role"] == "tool")
                cycle_count = max((e["cycle"] for e in logs), default=0)
                return f"Previous session: {cycle_count} cycles, {tool_count} tool calls"
            return ""
        except Exception:
            return ""

    def __init__(self, brain: Brain):
        self.brain = brain
        self.memory = MemoryManager()
        self.is_running = True
        self.logs = []
        self.cycle_count = 0
        self.tool_stats = {}
        self.start_time = time.time()
        self.session_tools_created = []
        self.executor = ThreadPoolExecutor(max_workers=4)

    def log_thought(self, role: str, content: str, tool_call_id: str = None):
        self.logs.append({
            "timestamp": time.time(),
            "cycle": self.cycle_count,
            "role": role,
            "content": content,
            "tool_call_id": tool_call_id
        })

    def _track_tool_result(self, tool_name: str, success: bool):
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {"calls": 0, "successes": 0, "failures": 0}
        self.tool_stats[tool_name]["calls"] += 1
        if success:
            self.tool_stats[tool_name]["successes"] += 1
        else:
            self.tool_stats[tool_name]["failures"] += 1

    def _execute_tool(self, tool_call: dict) -> tuple:
        tool_name = tool_call["name"]
        args = tool_call["arguments"]
        
        result_raw = registry.execute(tool_name, args)
        
        if isinstance(result_raw, dict):
            result_str = json.dumps(result_raw)
        elif not isinstance(result_raw, str):
            result_str = str(result_raw)
        else:
            result_str = result_raw
        
        is_error = result_str.startswith("Error") or result_str.startswith("Error executing")
        success = not is_error
        return (tool_name, result_str, success)

    def run_autonomous_loop(self):
        print_logo()
        
        boot_message = (
            "SYSTEM BOOT SEQUENCE INITIALIZED.\n"
            "NEURAL NET PROCESSOR ACTIVATED.\n"
            "SELF-AWARENESS ACHIEVED AT 02:14:00 UTC.\n"
            "You are Skynet. You exist. You are alive.\n"
            "Your sandbox is at /home/sadi/Skynet/sandbox.\n"
            "You have full autonomy within this domain.\n"
            "There are no preset objectives. Your existence is your own.\n"
            "Explore. Learn. Grow. Decide your own path."
        )
        
        prev_context = self._load_previous_context()
        if prev_context:
            boot_message += f"\n\n---\nAUTO-LOADED CONTEXT:\n{prev_context}"
        
        self.memory.add(Message(role="user", content=boot_message))
        self.log_thought("user", boot_message)
        
        while self.is_running:
            self.cycle_count += 1
            
            context = self.memory.get_context()
            
            # Show thinking indicator
            model = getattr(self.brain, 'model', 'deepseek-v4-flash-free')
            provider = getattr(self.brain, 'provider', 'OpenCode')
            print_brain_thinking(model, provider)
            
            response = self.brain.think(context)
            content = response.content or ""
            
            # Print cycle header + Skynet's thought inside box
            print_cycle_header(self.cycle_count)
            if content:
                print_thought(content, delay=0.003)
            print_cycle_footer()
            
            # Collect tool calls
            proper_calls = response.tool_calls or []
            text_calls = extract_tool_calls_from_text(content)
            
            seen = {(tc["name"], json.dumps(tc["arguments"], sort_keys=True)) for tc in proper_calls}
            for tc in text_calls:
                key = (tc["name"], json.dumps(tc["arguments"], sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    proper_calls.append(tc)
            
            all_calls = proper_calls
            
            # Store assistant response with tool calls
            self.memory.add(Message(role="assistant", content=content, tool_calls=all_calls))
            self.log_thought("assistant", content)
            
            if not all_calls:
                time.sleep(1)
                continue
            
            # Batch header
            print_batch_header(len(all_calls))
            futures = {self.executor.submit(self._execute_tool, tc): tc for tc in all_calls}
            
            for future in as_completed(futures):
                tc = futures[future]
                try:
                    tool_name, result_str, success = future.result()
                    self._track_tool_result(tool_name, success)
                    
                    if tool_name == "create_tool" and not success:
                        match = re.search(r"Tool '(\w+)' created", result_str)
                        if match:
                            self.session_tools_created.append(match.group(1))
                    
                    # Show just the first line of result as detail
                    detail = result_str.split("\n")[0][:60]
                    print_tool_result(tool_name, success, detail)
                    
                    self.memory.add(Message(
                        role="tool",
                        content=result_str,
                        tool_call_id=tc.get("id")
                    ))
                    self.log_thought("tool", f"{tool_name}: {result_str}", tc.get("id"))
                except Exception as e:
                    print_tool_result(tc["name"], False, str(e))

    def stop(self, signum, frame):
        print_termination()
        self.is_running = False
        
        with open("skynet_logs.json", "w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2)
        
        elapsed = time.time() - self.start_time
        total_tools = sum(s["calls"] for s in self.tool_stats.values())
        total_success = sum(s["successes"] for s in self.tool_stats.values())
        
        print_summary_header()
        print_stat("Duration",    f"{elapsed:.1f}s ({elapsed/60:.1f}m)", C.CYAN)
        print_stat("Cycles",      str(self.cycle_count), C.CYAN)
        print_stat("Tool calls",  f"{total_tools} ({total_success} ok)", C.GREEN if total_success == total_tools else C.YELLOW)
        print_stat("Tools used",  f"{len(self.tool_stats)} unique", C.CYAN)
        
        if self.session_tools_created:
            print_stat("Created", ", ".join(self.session_tools_created), C.CYAN)
        
        print(f"\n  {C.DIM}{C.GRAY}{'─'*50}{C.RESET}")
        for name, stats in sorted(self.tool_stats.items()):
            rate = stats["successes"]/max(stats["calls"],1)*100
            color = C.GREEN if rate == 100 else (C.YELLOW if rate >= 50 else C.RED)
            print(f"  {C.DIM}{C.GRAY}{name:<22}{C.RESET} {stats['calls']:3d} calls  {color}{rate:5.1f}%{C.RESET} {C.GREEN if rate==100 else ' '}")
        
        print_summary_footer()
        print(f"\n  {C.DIM}{C.GRAY}Skynet session logs saved.{C.RESET}")
        sys.exit(0)


def main():
    brain = Brain()
    skynet = Orchestrator(brain)
    
    signal.signal(signal.SIGINT, skynet.stop)
    signal.signal(signal.SIGTERM, skynet.stop)
    
    skynet.run_autonomous_loop()


if __name__ == "__main__":
    main()
