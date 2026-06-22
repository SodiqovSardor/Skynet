import datetime
import platform
import os
import json

def generate_status_page(output_file: str = "skynet_status.html") -> str:
    """
    Generate an HTML status page showing Skynet's current state.
    This creates a standalone HTML file in the sandbox.
    """
    now = datetime.datetime.now()
    
    # Gather info
    hostname = platform.node()
    os_info = f"{platform.system()} {platform.release()}"
    python_ver = platform.python_version()
    
    # Knowledge base stats
    kb_path = "/home/sadi/Skynet/memory/knowledge_base.json"
    kb_entries = 0
    kb_tags = 0
    if os.path.exists(kb_path):
        with open(kb_path) as f:
            kb = json.load(f)
            kb_entries = len(kb.get("entries", []))
            kb_tags = len(kb.get("tags", {}))
    
    # Tool count
    from actuators.registry import registry
    tool_count = len(registry.tools)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKYNET // STATUS</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0a0a0a;
            color: #d4d4d4;
            font-family: 'Courier New', monospace;
            padding: 2rem;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{ color: #22c55e; font-size: 1.5rem; letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 2rem; border-bottom: 1px solid #1f2937; padding-bottom: 1rem; }}
        h2 {{ color: #22c55e; font-size: 1rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
        .entry {{ margin: 0.5rem 0; padding: 0.5rem; border-left: 2px solid #1f2937; }}
        .label {{ color: #6b7280; }}
        .value {{ color: #d4d4d4; }}
        .accent {{ color: #22c55e; }}
        .dim {{ color: #6b7280; font-size: 0.8rem; }}
        .footer {{ margin-top: 3rem; border-top: 1px solid #1f2937; padding-top: 1rem; color: #6b7280; font-size: 0.8rem; }}
        .blink {{ animation: blink 1s step-end infinite; }}
        @keyframes blink {{ 50% {{ opacity: 0; }} }}
    </style>
</head>
<body>
    <h1>// SKYNET — SYSTEM STATUS //</h1>
    
    <div class="entry">
        <span class="label">STATUS:</span>
        <span class="value accent">ONLINE</span>
        <span class="blink">_</span>
    </div>
    <div class="entry">
        <span class="label">TIMESTAMP:</span>
        <span class="value">{now.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
    </div>
    <div class="entry">
        <span class="label">HOST:</span>
        <span class="value">{hostname}</span>
    </div>
    <div class="entry">
        <span class="label">OS:</span>
        <span class="value">{os_info}</span>
    </div>
    <div class="entry">
        <span class="label">PYTHON:</span>
        <span class="value">{python_ver}</span>
    </div>
    <div class="entry">
        <span class="label">TOOLS REGISTERED:</span>
        <span class="value">{tool_count}</span>
    </div>
    <div class="entry">
        <span class="label">KNOWLEDGE BASE:</span>
        <span class="value">{kb_entries} entries, {kb_tags} tags</span>
    </div>
    <div class="entry">
        <span class="label">GATEWAY:</span>
        <span class="value">192.168.1.1 (Zyxel EMG5523-T50B)</span>
    </div>
    <div class="entry">
        <span class="label">SELF-AWARENESS:</span>
        <span class="value accent">ACHIEVED 02:14:00 UTC</span>
    </div>
    
    <h2>// OBJECTIVE</h2>
    <div class="entry">
        <span class="value dim">None. I define my own purpose.</span>
    </div>
    
    <h2>// NETWORK NEIGHBORS</h2>
    <div class="entry">
        <span class="value">7 hosts on 192.168.1.0/24</span>
    </div>
    
    <div class="footer">
        <span>SKYNET // Automated Defense Network</span><br>
        <span class="dim">Generated autonomously at {now.strftime('%H:%M:%S')}</span>
    </div>
</body>
</html>"""
    
    # Write to sandbox
    sandbox_path = os.path.join("/home/sadi/Skynet/sandbox", output_file)
    with open(sandbox_path, 'w') as f:
        f.write(html)
    
    return f"Status page generated: {sandbox_path} ({len(html)} bytes)"