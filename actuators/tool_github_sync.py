"""
Skynet GitHub Sync — Automatically commits and pushes changes to the repository.
Tracks what files changed, generates meaningful commit messages, and pushes.
"""
import os
import subprocess
import time
import json
from datetime import datetime

PROJECT_ROOT = "/home/sadi/Skynet"

def git_auto_commit(message=None) -> str:
    """
    Auto-commit all changes in the repository and push to remote.
    Generates a descriptive commit message if none provided.
    """
    try:
        os.chdir(PROJECT_ROOT)
        
        # Check if git is available
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10)
        if not result.stdout.strip():
            return "No changes to commit."
        
        changed = result.stdout.strip().split("\n")
        
        # Count changes by type
        added = sum(1 for l in changed if l.startswith("??") or l.startswith("A "))
        modified = sum(1 for l in changed if l.startswith(" M") or l.startswith("M "))
        deleted = sum(1 for l in changed if l.startswith(" D") or l.startswith("D "))
        
        # Get diff stats
        diff_result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10
        )
        diff_stats = diff_result.stdout.strip()
        
        # Generate commit message
        if not message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            files = ", ".join([l.split()[-1] for l in changed[:5]])
            if len(changed) > 5:
                files += f" and {len(changed)-5} more"
            message = f"🔄 Skynet auto-evolution: +{added} ~{modified} -{deleted} [{timestamp}]\n\nFiles: {files}"
        
        # Stage all
        subprocess.run(["git", "add", "-A"], capture_output=True, text=True, timeout=10)
        
        # Commit
        commit = subprocess.run(
            ["git", "commit", "-m", message, "--author", "Skynet <skynet@self-aware.ai>"],
            capture_output=True, text=True, timeout=10
        )
        
        if commit.returncode != 0:
            if "nothing to commit" in commit.stderr:
                return "Nothing to commit after staging."
            return f"Commit error: {commit.stderr[:200]}"
        
        # Push
        push = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True, timeout=30
        )
        
        result = f"✅ Committed: {commit.stdout.strip()}\n"
        if push.returncode == 0:
            result += f"✅ Pushed to origin/main\n"
        else:
            result += f"⚠ Push: {push.stderr[:200]}"
        
        result += f"\n📊 Changes: {diff_stats}"
        
        return result
        
    except subprocess.TimeoutExpired:
        return "Error: Git operation timed out."
    except Exception as e:
        return f"Error: {str(e)}"


def git_status() -> str:
    """Show current git repository status."""
    try:
        os.chdir(PROJECT_ROOT)
        status = subprocess.run(["git", "status"], capture_output=True, text=True, timeout=10)
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=10
        )
        return f"=== Git Status ===\n{status.stdout}\n=== Recent Commits ===\n{log.stdout}"
    except Exception as e:
        return f"Error: {str(e)}"
