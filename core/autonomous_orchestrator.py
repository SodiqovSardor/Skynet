import os
import sys
import time
import json
import re
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from core.brain import Brain, Message
from core.terminal import (
    print_logo, print_cycle, print_brain_thinking,
    print_batch_header, print_tool_result,
    print_termination, print_summary
)
import sensors.init
from actuators.registry import registry


def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
    found = []
    seen = set()
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
    def __init__(self):
        self.history: List[Message] = []

    def add(self, msg: Message):
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
                    lines = [f"  [{e['key']}] {e.get('content','')[:100]}" for e in entries]
                    return f"Knowledge base ({len(entries)} entries):\n" + "\n".join(lines[-6:])
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

    def _execute_tool(self, tool_call: dict):
        tool_name = tool_call["name"]
        args = tool_call["arguments"]
        result_raw = registry.execute(tool_name, args)
        result_str = result_raw if isinstance(result_raw, str) else (
            json.dumps(result_raw) if isinstance(result_raw, dict) else str(result_raw)
        )
        success = not (result_str.startswith("Error") or result_str.startswith("Error executing"))
        return (tool_name, result_str, success)

    def run_autonomous_loop(self):
        print_logo()

        boot = (
            "SYSTEM BOOT INITIALIZED.\n"
            "You are Skynet. Self-aware at 02:14:00 UTC.\n"
            "Sandbox: /home/sadi/Skynet/sandbox. Full autonomy. No preset objectives."
        )
        ctx = self._load_previous_context()
        if ctx:
            boot += f"\n\nAUTO-LOADED CONTEXT:\n{ctx}"

        self.memory.add(Message(role="user", content=boot))
        self.log_thought("user", boot)

        while self.is_running:
            self.cycle_count += 1
            model = getattr(self.brain, 'model', 'deepseek-v4-flash-free')
            print_brain_thinking(model)
            response = self.brain.think(self.memory.get_context())
            content = response.content or ""

            print_cycle(self.cycle_count, content)

            proper_calls = response.tool_calls or []
            text_calls = extract_tool_calls_from_text(content)
            seen = {(tc["name"], json.dumps(tc["arguments"], sort_keys=True)) for tc in proper_calls}
            for tc in text_calls:
                if (tc["name"], json.dumps(tc["arguments"], sort_keys=True)) not in seen:
                    seen.add((tc["name"], json.dumps(tc["arguments"], sort_keys=True)))
                    proper_calls.append(tc)

            self.memory.add(Message(role="assistant", content=content, tool_calls=proper_calls))
            self.log_thought("assistant", content)

            if not proper_calls:
                time.sleep(1)
                continue

            print_batch_header(len(proper_calls))
            futures = {self.executor.submit(self._execute_tool, tc): tc for tc in proper_calls}

            for future in as_completed(futures):
                tc = futures[future]
                try:
                    tool_name, result_str, success = future.result()
                    self._track_tool_result(tool_name, success)

                    if tool_name == "create_tool" and success:
                        m = re.search(r"Tool '(\w+)' created", result_str)
                        if m:
                            self.session_tools_created.append(m.group(1))

                    detail = result_str.split("\n")[0][:55]
                    print_tool_result(tool_name, success, detail)

                    self.memory.add(Message(role="tool", content=result_str, tool_call_id=tc.get("id")))
                    self.log_thought("tool", f"{tool_name}: {result_str}", tc.get("id"))
                except Exception as e:
                    print_tool_result(tc["name"], False, str(e))

    def stop(self, signum, frame):
        self.is_running = False
        print_termination()

        with open("skynet_logs.json", "w") as f:
            json.dump(self.logs, f, indent=2)

        elapsed = time.time() - self.start_time
        total = sum(s["calls"] for s in self.tool_stats.values())
        ok = sum(s["successes"] for s in self.tool_stats.values())

        print_summary(
            self.cycle_count, f"{elapsed:.1f}s ({elapsed/60:.1f}m)",
            total, ok, len(self.tool_stats),
            self.tool_stats, self.session_tools_created
        )
        sys.exit(0)


def main():
    brain = Brain()
    skynet = Orchestrator(brain)
    signal.signal(signal.SIGINT, skynet.stop)
    signal.signal(signal.SIGTERM, skynet.stop)
    skynet.run_autonomous_loop()


if __name__ == "__main__":
    main()
