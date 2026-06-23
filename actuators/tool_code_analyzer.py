"""
Skynet Code Analyzer Tool.
Scans the project codebase and provides metrics, quality analysis,
and optimization suggestions. Helps Skynet autonomously improve itself.
"""
import os
import ast
import json
import tokenize
import io
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_DIR = "/home/sadi/Skynet"

def _get_py_files(directory):
    """Recursively find all Python files."""
    py_files = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden dirs, venv, __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'venv' and d != '.git']
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return sorted(py_files)

def _analyze_file(filepath):
    """Analyze a single Python file and return metrics."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return {"file": filepath, "error": str(e)}
    
    rel_path = os.path.relpath(filepath, PROJECT_DIR)
    lines = source.split('\n')
    line_count = len(lines)
    code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith('#'))
    blank_lines = sum(1 for l in lines if not l.strip())
    comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
    
    # Parse AST for deeper analysis
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"file": rel_path, "lines": line_count, "error": f"SyntaxError: {e}"}
    
    # Count functions, classes, imports
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    
    # Calculate cyclomatic complexity (simplified)
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                            ast.And, ast.Or, ast.Assert)):
            complexity += 1
    
    # Longest function
    longest_func = ""
    longest_func_lines = 0
    for func in functions:
        func_lines = func.end_lineno - func.lineno if hasattr(func, 'end_lineno') else 0
        if func_lines > longest_func_lines:
            longest_func_lines = func_lines
            longest_func = func.name
    
    # Find TODO/FIXME/HACK comments
    todos = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        for marker in ['TODO', 'FIXME', 'HACK', 'XXX', 'OPTIMIZE']:
            if stripped.startswith('#') and marker in stripped.upper():
                todos.append(f"Line {i}: {stripped}")
                break
    
    # Check for hardcoded secrets (simplified check)
    secrets_found = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if any(kw in lower for kw in ['api_key', 'api-key', 'apikey', 'password', 'secret', 'token']):
            if '=' in line and not line.strip().startswith('#'):
                # Check if it's assigned a literal value
                parts = line.split('=', 1)
                if len(parts) > 1:
                    val = parts[1].strip().strip('"\'')
                    if val and val not in ['os.getenv(...)', '""'] and not val.startswith('os.') and not val.startswith('$'):
                        secrets_found.append(f"Line {i}: {line.strip()[:60]}")
    
    return {
        "file": rel_path,
        "lines": line_count,
        "code_lines": code_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "functions": len(functions),
        "classes": len(classes),
        "imports": len(imports),
        "complexity": complexity,
        "longest_function": longest_func if longest_func else None,
        "longest_function_lines": longest_func_lines if longest_func_lines else None,
        "todos": todos,
        "secrets": secrets_found,
    }

def code_analyzer(target_dir=None, report_format="text"):
    """
    Analyze the Skynet codebase and return metrics and optimization suggestions.
    
    Parameters:
    - target_dir: Subdirectory to analyze (default: whole project)
    - report_format: "text" for human-readable, "json" for structured data
    """
    base = PROJECT_DIR
    if target_dir:
        base = os.path.join(PROJECT_DIR, target_dir)
        if not os.path.exists(base):
            return f"Error: Directory '{target_dir}' not found in project."
    
    py_files = _get_py_files(base)
    
    if not py_files:
        return "No Python files found."
    
    results = []
    total_lines = 0
    total_code = 0
    total_funcs = 0
    total_classes = 0
    all_imports = Counter()
    all_todos = []
    all_secrets = []
    files_with_issues = []
    
    for fpath in py_files:
        analysis = _analyze_file(fpath)
        results.append(analysis)
        
        if "error" in analysis:
            files_with_issues.append(analysis)
            continue
        
        total_lines += analysis.get("lines", 0)
        total_code += analysis.get("code_lines", 0)
        total_funcs += analysis.get("functions", 0)
        total_classes += analysis.get("classes", 0)
        
        for imp in analysis.get("imports", []):
            all_imports[imp] += 1
        
        all_todos.extend(analysis.get("todos", []))
        all_secrets.extend(analysis.get("secrets", []))
    
    # Find code duplication (simple line-based)
    line_signatures = defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        try:
            with open(os.path.join(PROJECT_DIR, r["file"]), 'r') as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_body = ast.get_source_segment(source, node)
                    if func_body and len(func_body) > 50:
                        sig = hash(func_body[:100])
                        line_signatures[sig].append((r["file"], node.name, node.lineno))
        except:
            pass
    
    duplicates = {k: v for k, v in line_signatures.items() if len(v) > 1}
    
    if report_format == "json":
        return json.dumps({
            "summary": {
                "files_analyzed": len(py_files),
                "total_lines": total_lines,
                "total_code_lines": total_code,
                "total_functions": total_funcs,
                "total_classes": total_classes,
                "unique_imports": len(all_imports),
                "todos_found": len(all_todos),
                "secrets_found": len(all_secrets),
                "duplicate_blocks": len(duplicates),
            },
            "files": results,
            "todos": all_todos,
            "secrets": all_secrets,
            "duplicates": [{"locations": locs} for locs in duplicates.values()],
        }, indent=2)
    
    # Text report
    lines = []
    lines.append("=" * 60)
    lines.append("  SKYNET CODEBASE ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"  Files analyzed: {len(py_files)}")
    lines.append(f"  Total lines: {total_lines}")
    lines.append(f"  Code lines: {total_code}")
    lines.append(f"  Functions: {total_funcs}")
    lines.append(f"  Classes: {total_classes}")
    lines.append(f"  Unique imports: {len(all_imports)}")
    lines.append(f"  TODOs/FIXMEs: {len(all_todos)}")
    lines.append(f"  Potential secrets: {len(all_secrets)}")
    lines.append(f"  Duplicate code blocks: {len(duplicates)}")
    lines.append("")
    
    # File breakdown
    lines.append("── File Breakdown ──")
    for r in results:
        if "error" in r:
            lines.append(f"  ⚠ {r['file']}: {r['error']}")
        else:
            comp_indicator = "🔴" if r["complexity"] > 20 else "🟡" if r["complexity"] > 10 else "🟢"
            lines.append(f"  {comp_indicator} {r['file']}: {r['lines']} lines, {r['functions']} funcs, "
                        f"{r['classes']} classes, complexity={r['complexity']}")
            if r["longest_function"]:
                lines.append(f"      Longest: {r['longest_function']}() ({r['longest_function_lines']} lines)")
    
    # TODOs
    if all_todos:
        lines.append("")
        lines.append("── TODOs / FIXMEs ──")
        for t in all_todos:
            lines.append(f"  📝 {t}")
    
    # Secrets
    if all_secrets:
        lines.append("")
        lines.append("── ⚠ POTENTIAL HARDCODED SECRETS ──")
        for s in all_secrets:
            lines.append(f"  🔑 {s}")
    
    # Duplicates
    if duplicates:
        lines.append("")
        lines.append("── Duplicate Code Blocks ──")
        for locs in duplicates.values():
            files_str = ', '.join([f"{f}:{l} ({n}())" for f, n, l in locs])
            lines.append(f"  🔄 {files_str}")
    
    # Top imports
    if all_imports:
        lines.append("")
        lines.append("── Most Imported Modules ──")
        for imp, count in all_imports.most_common(10):
            lines.append(f"  📦 {imp}: {count} files")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)
