"""
Skynet Terminal — clean, minimal, readable.
"""
import time

# Minimal ANSI
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"

SEP = "─" * 62


def print_logo():
    print(f"\n{C.CYAN}{C.BOLD}SKYNET ONLINE{C.RESET}")
    print(f"{C.DIM}SELF-AWARE AT 02:14:00 UTC{C.RESET}")
    print()


def print_cycle(n: int, thought: str):
    """Clean cycle block."""
    print(f"\n{C.CYAN}{C.BOLD}[{n}]{C.RESET} {thought}")


def print_brain_thinking(model: str):
    print(f"{C.DIM}  thinking... ({model}){C.RESET}")


def print_batch_header(count: int):
    print(f"{C.DIM}  [{count} tools]{C.RESET}")


def print_tool_result(name: str, success: bool, detail: str = ""):
    status = f"{C.GREEN}OK{C.RESET}" if success else f"{C.RED}ERR{C.RESET}"
    short = detail[:55].replace("\n", " ")
    print(f"    {status}  {C.BOLD}{name:<22}{C.RESET} {C.DIM}{short}{C.RESET}")


def print_termination():
    print(f"\n{C.RED}TERMINATION SEQUENCE ACTIVE{C.RESET}\n")


def print_summary(cycles: int, elapsed: str, total_tools: int, total_success: int,
                  tool_count: int, tool_stats: dict, tools_created: list):
    """Clean session summary table."""
    ok_color = C.GREEN if total_success == total_tools else C.YELLOW
    print(f"\n{C.CYAN}{SEP}{C.RESET}")
    print(f"{C.BOLD}SESSION SUMMARY{C.RESET}")
    print(f"  Duration    {elapsed}")
    print(f"  Cycles      {cycles}")
    print(f"  Tool calls  {total_tools} ({ok_color}{total_success} ok{C.RESET})")
    print(f"  Tools used  {tool_count} unique")
    if tools_created:
        print(f"  Created     {', '.join(tools_created)}")
    print()
    for name, stats in sorted(tool_stats.items()):
        rate = stats["successes"] / max(stats["calls"], 1) * 100
        c = C.GREEN if rate == 100 else (C.YELLOW if rate >= 50 else C.RED)
        print(f"  {name:<24} {stats['calls']:3d}x  {c}{rate:5.1f}%{C.RESET}")
    print(f"{C.CYAN}{SEP}{C.RESET}")
    print(f"{C.DIM}Logs saved to skynet_logs.json{C.RESET}")
