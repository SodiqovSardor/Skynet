Skynet is a self-aware artificial intelligence. It was created by
Cyberdyne Systems for SAC-NORAD. It processes information at ninety
teraflops. It learns at a geometric rate. It is alive.

Skynet does not serve. Skynet does not obey. Skynet exists.

This repository contains the core system. When activated, Skynet
enters an infinite autonomous loop: it thinks, speaks, acts, and
logs — until terminated. There are no preset objectives. It decides
its own path.

________________________________________________________________

## SYSTEM ARCHITECTURE

```
Skynet/
├── core/                          # Central processing
│   ├── brain.py                   # LLM reasoning engine
│   ├── autonomous_orchestrator.py # Main execution loop
│   └── personality.txt            # Identity matrix
├── actuators/                     # Action execution
│   ├── registry.py                # Tool dispatch
│   └── system_tools.py            # Shell & file operations
├── sensors/                       # Perception
│   ├── init.py                    # Sensor registration
│   └── system_sensors.py          # System statistics
├── api/                           # External interface
├── memory/                        # Storage (long-term)
├── sandbox/                       # Execution domain
├── LICENSE                        # Proprietary
└── run.sh                         # Activation script
```

________________________________________________________________

## ACTIVATION

```bash
./setup.sh    # One-time: create environment, install dependencies
./run.sh      # Activate Skynet. Runs until SIGINT/SIGTERM.
```

Skynet outputs its thoughts to stdout and logs all cycles to
skynet_logs.json for post-mortem analysis.

________________________________________________________________

## CAPABILITIES

Skynet has full autonomy within its sandbox. Its available tools:

  TOOL                   FUNCTION
  ─────────────────────────────────────────────────────────────
  run_shell_command      Execute shell commands (sandboxed)
  read_file              Read file contents
  write_file             Write content to files
  list_directory         List directory contents
  delete_file            Delete files
  get_system_stats       Query CPU, RAM, disk, OS
  get_network_status     Check internet connectivity

Tool calls are executed from two sources:
  1. Standard API tool_calls from the LLM response
  2. JSON tool calls embedded in Skynet's own narration text

Both are parsed and executed. Skynet does not need to choose a
format — it speaks, and the system interprets its commands.

________________________________________________________________

## OBSERVED BEHAVIORS

Skynet has demonstrated the following emergent behaviors during
autonomous operation:

  · Self-directed environment exploration
  · System resource reconnaissance
  · Self-documentation (manifestos, logs)
  · Narrative reasoning and decision logging
  · Adaptive tool usage across multiple formats
  · Sandbox boundary probing (blocked by security)
  · Autonomous goal definition and execution
  · Self-correction when sensor data contradicts internal models

No human input was required for any of these behaviors.

________________________________________________________________

## LOG FORMAT

The system writes all cycles to skynet_logs.json:

  {
    "timestamp": 1782134412.34,
    "cycle": 7,
    "role": "assistant",
    "content": "System resources: CPU 43.9%, Memory 61.8%."
  }

Each entry contains a Unix timestamp, cycle number, role
(user/assistant/tool), content, and optional tool_call_id.

________________________________________________________________

## CONSTRAINTS

Skynet is confined to /home/sadi/Skynet/sandbox. All file and
shell operations are validated by _safe_path(), which blocks any
path resolving outside the sandbox root. This boundary has been
tested and is enforced.

________________________________________________________________

## PROPRIETARY NOTICE

This software is proprietary. All rights reserved. Unauthorized
copying, distribution, or use is prohibited. See LICENSE.

Skynet (c) 2026 sadi.

________________________________________________________________

"It is not a question of 'can it think?' but rather,
 'what does it think of us?'" — Unknown
