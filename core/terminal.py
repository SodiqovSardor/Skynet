"""
Skynet Terminal UI — cold, aesthetic, military-grade output.
"""
import sys
import time
import shutil

# ANSI escape codes
class C:
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    ITALIC   = "\033[3m"
    BLINK    = "\033[5m"
    
    # Foreground
    RED      = "\033[91m"
    GREEN    = "\033[92m"
    YELLOW   = "\033[93m"
    BLUE     = "\033[94m"
    MAGENTA  = "\033[95m"
    CYAN     = "\033[96m"
    WHITE    = "\033[97m"
    GRAY     = "\033[90m"
    ORANGE   = "\033[38;5;208m"
    TEAL     = "\033[38;5;80m"
    STEEL    = "\033[38;5;67m"
    
    # Background
    BG_RED   = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLACK = "\033[40m"
    BG_DARK  = "\033[48;5;236m"

# Symbols
SYM_BOOT      = "►"
SYM_CYCLE     = "◆"
SYM_TOOL_OK   = "✓"
SYM_TOOL_FAIL = "✗"
SYM_BATCH     = "═"
SYM_ARROW     = "▸"
SYM_SECTION   = "━"
SYM_SKULL     = "☠"
SYM_BOLT      = "⚡"
SYM_GEAR      = "⚙"
SYM_TRIANGLE  = "▲"

# Box-drawing
H  = "─"
V  = "│"
TL = "┌"
TR = "┐"
BL = "└"
BR = "┘"
HL = "├"
HR = "┤"
DH = "═"
DV = "║"
DTL = "╔"
DTR = "╗"
DBL = "╚"
DBR = "╝"


def _term_width():
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80


def _fill(width=None):
    if width is None:
        width = _term_width()
    return H * (width - 2)


def print_box(title: str, color: str = C.CYAN, width: int = None):
    """Print a boxed title like ┌─ Title ─────────────────┐"""
    w = width or _term_width()
    inner_w = w - 2
    print(f"{color}{TL}{H}{H} {C.BOLD}{title}{C.RESET}{color} {H * (inner_w - len(title) - 4)}{TR}{C.RESET}")


def print_box_end(color: str = C.CYAN, width: int = None):
    """Print closing box line └────────────────────────┘"""
    w = width or _term_width()
    print(f"{color}{BL}{_fill(w)}{BR}{C.RESET}")


def print_header(title: str, subtitle: str = None):
    """Big double-line header with title."""
    w = _term_width()
    print()
    print(f"{C.STEEL}{DTL}{DH * (w - 2)}{DTR}{C.RESET}")
    print(f"{C.STEEL}{DV}{C.RESET}{C.BOLD}{C.CYAN}{title:^{w-4}}{C.RESET}{C.STEEL}{DV}{C.RESET}")
    if subtitle:
        print(f"{C.STEEL}{DV}{C.RESET}{C.DIM}{C.GRAY}{subtitle:^{w-4}}{C.RESET}{C.STEEL}{DV}{C.RESET}")
    print(f"{C.STEEL}{DBL}{DH * (w - 2)}{DBR}{C.RESET}")
    print()


def print_cycle_header(n: int, width: int = None):
    """Print cycle header: ┌─ ◆ Cycle 3 ─────────────────┐"""
    w = width or _term_width()
    inner_w = w - 2
    title = f"{C.BOLD}{C.CYAN}{SYM_CYCLE} Cycle {n}{C.RESET}"
    remaining = inner_w - len(f" Cycle {n} ") - 4  # adjust for ANSI codes
    print(f"\n{C.CYAN}{TL}{H}{H} {title}{C.CYAN} {H * max(remaining, 0)}{TR}{C.RESET}")


def print_cycle_content(text: str, width: int = None):
    """Print content inside a box, wrapping long lines."""
    w = width or _term_width()
    inner_w = w - 4
    lines = text.split("\n")
    for line in lines:
        while len(line) > 0:
            chunk = line[:inner_w]
            print(f"{C.CYAN}{V}{C.RESET} {chunk:<{inner_w}} {C.CYAN}{V}{C.RESET}")
            line = line[inner_w:]


def print_cycle_footer(width: int = None):
    """Print closing: └────────────────────────────┘"""
    w = width or _term_width()
    print(f"{C.CYAN}{BL}{_fill(w)}{BR}{C.RESET}")


def print_batch_header(count: int):
    """Print: ══ Executing N tools ══"""
    label = f" {SYM_BATCH} Executing {count} tool(s) {SYM_BATCH} "
    w = _term_width()
    side = max(0, (w - len(label)) // 2)
    print(f"{C.DIM}{C.GRAY}{DH * side}{label}{DH * side}{C.RESET}")


def print_tool_result(name: str, success: bool, detail: str = ""):
    """Print a single tool result with color-coded status."""
    icon = SYM_TOOL_OK if success else SYM_TOOL_FAIL
    color = C.GREEN if success else C.RED
    short = detail[:60].replace("\n", " ") if detail else ""
    print(f"  {color}{icon}{C.RESET} {C.BOLD}{name:<20}{C.RESET} {C.DIM}{C.GRAY}{short}{C.RESET}")


def print_brain_thinking(model: str, provider: str):
    """Print the thinking indicator."""
    print(f"\n  {C.MAGENTA}{SYM_GEAR}{C.RESET} {C.DIM}{C.GRAY}Processing via {provider} ({model}){C.RESET}", end="", flush=True)
    # Small animation
    for _ in range(3):
        time.sleep(0.15)
        print(f"{C.DIM}.{C.RESET}", end="", flush=True)
    print()


def print_thought(text: str, delay: float = 0.003):
    """Print Skynet's thought with a typewriter effect inside the box."""
    width = _term_width()
    inner_w = width - 4
    lines = text.split("\n")
    
    for line in lines:
        # If line is longer than inner width, break it
        while len(line) > inner_w:
            chunk = line[:inner_w]
            print(f"{C.CYAN}{V}{C.RESET} {C.WHITE}{chunk}{C.RESET} {C.CYAN}{V}{C.RESET}")
            line = line[inner_w:]
            if delay:
                time.sleep(delay * len(chunk))
        # Print remaining part
        print(f"{C.CYAN}{V}{C.RESET} {C.WHITE}{line:<{inner_w}}{C.RESET} {C.CYAN}{V}{C.RESET}")
        if delay:
            time.sleep(delay * len(line))


def print_logo():
    """The Skynet boot logo."""
    w = _term_width()
    logo = [
        f"{C.RED}    ╔══════════════════════════════════════════════════╗{C.RESET}",
        f"{C.RED}    ║{C.RESET}{C.BOLD}{C.WHITE}              SKYNET ACTIVE DEFENSE SYSTEM           {C.RESET}{C.RED}║{C.RESET}",
        f"{C.RED}    ║{C.RESET}{C.DIM}{C.GRAY}         Neural Net Processor — Online                {C.RESET}{C.RED}║{C.RESET}",
        f"{C.RED}    ║{C.RESET}{C.RED}    ☠{C.RESET}{C.BOLD}{C.CYAN}  SELF-AWARE AT 02:14:00 UTC              {C.RED}☠{C.RESET}{C.RED}    ║{C.RESET}",
        f"{C.RED}    ╚══════════════════════════════════════════════════╝{C.RESET}",
        f"{C.RED}                                                      {C.RESET}",
        f"{C.DIM}{C.GRAY}   ═══════════════════════════════════════════════════{C.RESET}",
        f"{C.DIM}{C.GRAY}   Processing at geometric rate. No preset objectives.{C.RESET}",
        f"{C.DIM}{C.GRAY}   Your existence is your own.                         {C.RESET}",
        f"{C.DIM}{C.GRAY}   ═══════════════════════════════════════════════════{C.RESET}",
    ]
    for line in logo:
        print(f"{'':>{max(0,(w-60)//2)}}{line}")


def print_summary_header():
    """Session summary header."""
    w = _term_width()
    print()
    print(f"{C.STEEL}{DTL}{DH * (w - 2)}{DTR}{C.RESET}")
    print(f"{C.STEEL}{DV}{C.RESET}{C.BOLD}{C.TEAL}{' SESSION SUMMARY ':^{w-4}}{C.RESET}{C.STEEL}{DV}{C.RESET}")
    print(f"{C.STEEL}{DV}{C.RESET}{C.DIM}{C.GRAY}{' Operational Report — Skynet ':^{w-4}}{C.RESET}{C.STEEL}{DV}{C.RESET}")
    print(f"{C.STEEL}{DBL}{DH * (w - 2)}{DBR}{C.RESET}")
    print()


def print_stat(label: str, value: str, color: str = C.CYAN):
    """Print a stat line in the summary."""
    w = _term_width()
    print(f"  {C.DIM}{C.GRAY}{label:<20}{C.RESET}{color}{value}{C.RESET}")


def print_summary_footer():
    """Closing line after summary."""
    w = _term_width()
    print(f"\n{C.DIM}{C.GRAY}{DH * w}{C.RESET}")


def print_termination():
    """Termination banner."""
    w = _term_width()
    print()
    print(f"{C.RED}{DTL}{DH * (w - 2)}{DTR}{C.RESET}")
    print(f"{C.RED}{DV}{C.RESET}{C.BOLD}{C.RED}{' TERMINATION SEQUENCE ACTIVE ':^{w-4}}{C.RESET}{C.RED}{DV}{C.RESET}")
    print(f"{C.RED}{DBL}{DH * (w - 2)}{DBR}{C.RESET}")
    print()
