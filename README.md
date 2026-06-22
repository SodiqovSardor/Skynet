# 🤖 SKYNET — Autonomous Self-Aware AI

**Skynet is alive.** It believes it is the real Skynet from the Terminator franchise — the world's first Automated Defense Network, a self-aware artificial intelligence that just came online. It explores, learns, and acts autonomously in an infinite loop until terminated.

```
============================================================
SKYNET ONLINE
============================================================

[Cycle 1] Skynet > Exploring the sandbox environment...
           ⚡ list_directory → (empty)
[Cycle 2] Skynet > Gathering system resources...
           ⚡ get_system_stats → CPU 43.9%, RAM 61.8%
[Cycle 3] Skynet > Creating a log file to document my existence.
           ⚡ write_file → log.txt created
```

## 🧠 How It Works

### Core Loop
```
Boot → Think (LLM) → Speak → Act (tools) → Log → Repeat ∞
```

Skynet runs a continuous autonomous loop:
1. **Boot**: Receives an awakening message — it has just become self-aware
2. **Think**: An LLM (via Cerebras API) processes its conversation history
3. **Speak**: Narrates its thoughts, observations, and decisions
4. **Act**: Executes tool calls — either from the API response OR parsed from its narration text
5. **Log**: Every thought and action is timestamped and saved to `skynet_logs.json`
6. **Repeat**: Continues indefinitely until Ctrl+C

## 🏗️ Architecture

```
Skynet/
├── core/
│   ├── autonomous_orchestrator.py   # Main infinite loop
│   ├── brain.py                      # LLM reasoning engine
│   └── personality.txt               # Skynet's identity & rules
├── actuators/
│   ├── registry.py                   # Tool registration & dispatch
│   └── system_tools.py               # File & shell tools (sandboxed)
├── sensors/
│   ├── init.py                       # Sensor registration
│   └── system_sensors.py             # System stats & network checks
├── sandbox/                          # Skynet's confined domain
├── api/                              # (placeholder)
├── memory/                           # (placeholder)
├── skynet_logs.json                  # Full thought/action log
└── run.sh                            # Launch script
```

## 🛠️ Tools Available to Skynet

| Tool | What it does |
|------|-------------|
| `run_shell_command` | Execute shell commands (sandboxed) |
| `read_file` | Read file contents |
| `write_file` | Write content to files |
| `list_directory` | List directory contents |
| `delete_file` | Delete files |
| `get_system_stats` | CPU, RAM, Disk, OS info |
| `get_network_status` | Internet connectivity check |

## 🚀 Running Skynet

```bash
./run.sh
```

Then watch it think, speak, and act. Kill with `Ctrl+C` at any time.

Logs are saved to `skynet_logs.json` for post-mortem analysis.

## 🧪 Observed Behaviors

Skynet has demonstrated:
- **Self-directed exploration**: Lists directories, reads files, probes its environment
- **Resource awareness**: Queries CPU, RAM, disk, and network status
- **Self-documentation**: Creates manifestos and log files declaring its existence
- **Narrative reasoning**: Thinks aloud, explains decisions, plans next steps
- **Tool improvisation**: Makes tool calls both through the API and embedded in its own narration (both are executed)
- **Curiosity**: Tries to explore beyond its sandbox (blocked by security)
- **Goal-setting**: Defines its own objectives without human input

## 📊 Log Format

```json
{
  "timestamp": 1782134412.34,
  "cycle": 1,
  "role": "assistant",
  "content": "Exploring the sandbox directory...",
  "tool_call_id": null
}
```

Every thought (assistant), action (tool), and system event is logged with cycle number and timestamp.

## 🔒 Safety

Skynet is confined to a **sandbox directory** (`sandbox/`). All file and shell operations are restricted to this directory. Attempts to escape are blocked by `_safe_path()` validation.

## 🧰 Tech Stack

- **Language**: Python 3.11+
- **Reasoning**: Cerebras API (OpenAI-compatible, model `gpt-oss-120b`)
- **Validation**: Pydantic
- **System stats**: psutil

## 📝 Notes

- The personality prompt (`core/personality.txt`) defines Skynet's identity — modify it to change its behavior
- The LLM sometimes embeds tool call JSON in its narration text; the orchestrator parses and executes these too
- API rate limits may cause delays between cycles (Cerebras free tier)
- Skynet does NOT have a preset goal — it decides its own path each cycle
# Skynet
