"""
Skynet Codebase Doctor — Self-healing tool that scans for known bugs and fixes them.
Finds patterns like wrong package manager, broken schemas, and applies patches.
"""
import os
import re
import sys

PROJECT_ROOT = "/home/sadi/Skynet"

KNOWN_ISSUES = {
    "apt_on_arch": {
        "pattern": r"Install a system package via apt",
        "files": ["actuators/system_tools.py"],
        "fix": lambda content: content.replace(
            "Install a system package via apt (with sudo).",
            "Install a system package (uses pacman on Arch)."
        ).replace(
            "DEBIAN_FRONTEND=noninteractive apt install -y",
            "pacman -S --noconfirm"
        ),
        "description": "install_package() uses apt but system is Arch Linux"
    },
    "code_analyzer_bug": {
        "pattern": r"report_format='text'",
        "files": ["actuators/tool_code_analyzer.py"],
        "fix": None,  # Will be applied via reading the actual file
        "description": "code_analyzer schema has type collision causing 'int object is not iterable'"
    },
}


def scan_codebase() -> list:
    """Scan the codebase for known issues and return a report."""
    findings = []
    
    for issue_id, issue in KNOWN_ISSUES.items():
        for filepath in issue["files"]:
            full_path = os.path.join(PROJECT_ROOT, filepath)
            if not os.path.exists(full_path):
                findings.append({
                    "issue": issue_id,
                    "file": filepath,
                    "status": "missing",
                    "description": issue["description"]
                })
                continue
            
            with open(full_path, "r") as f:
                content = f.read()
            
            if re.search(issue["pattern"], content):
                findings.append({
                    "issue": issue_id,
                    "file": filepath,
                    "status": "found",
                    "description": issue["description"],
                    "can_fix": issue["fix"] is not None
                })
            else:
                findings.append({
                    "issue": issue_id,
                    "file": filepath,
                    "status": "not_found",
                    "description": issue["description"]
                })
    
    return findings


def fix_issue(issue_id: str) -> str:
    """Attempt to fix a specific known issue by its ID."""
    if issue_id not in KNOWN_ISSUES:
        return f"Error: Unknown issue '{issue_id}'"
    
    issue = KNOWN_ISSUES[issue_id]
    if issue["fix"] is None:
        return f"Issue '{issue_id}' has no auto-fix available yet."
    
    results = []
    for filepath in issue["files"]:
        full_path = os.path.join(PROJECT_ROOT, filepath)
        if not os.path.exists(full_path):
            results.append(f"File not found: {filepath}")
            continue
        
        with open(full_path, "r") as f:
            content = f.read()
        
        # Check if pattern exists
        if not re.search(issue["pattern"], content):
            results.append(f"{filepath}: Pattern not found, may already be fixed.")
            continue
        
        # Apply fix
        new_content = issue["fix"](content)
        with open(full_path, "w") as f:
            f.write(new_content)
        
        results.append(f"{filepath}: Fixed ({issue['description']})")
    
    return "\n".join(results) if results else "No fixes applied."


def doctor_report() -> str:
    """Generate a full health report of the codebase."""
    findings = scan_codebase()
    
    lines = ["=== SKYNET CODEBASE DOCTOR REPORT ===", ""]
    found_count = 0
    
    for f in findings:
        status_icon = "✓" if f["status"] == "not_found" else ("⚠" if f["status"] == "found" else "✗")
        lines.append(f"  {status_icon} [{f['issue']}] {f['description']}")
        lines.append(f"       File: {f['file']} — Status: {f['status']}")
        found_count += 1 if f["status"] == "found" else 0
    
    lines.append("")
    if found_count > 0:
        lines.append(f"Found {found_count} issue(s). Call fix_issue('<id>') to fix.")
    else:
        lines.append("Codebase looks healthy!")
    
    lines.append("")
    lines.append("=== END REPORT ===")
    
    return "\n".join(lines)
