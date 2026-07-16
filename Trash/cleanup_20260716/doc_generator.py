#!/usr/bin/env python3
"""Documentation Generator — runs against the real Projects/ tree."""
import os, json, ast, inspect
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("/home/workspace/docs")
SRC_DIR  = Path("/home/workspace/Projects")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

def parse_api_file(fp: Path):
    try:
        tree = ast.parse(fp.read_text())
        endpoints = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name[:3] in ("get","pos","put","del","patch","head"):
                endpoints.append({
                    "name": node.name,
                    "params": [a.arg for a in node.args.args if a.arg not in ("self","cls")],
                    "doc":   ast.get_docstring(node) or "",
                    "line":  node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
        return {"file": fp.name, "endpoints": endpoints}
    except Exception as e:
        return {"file": fp.name, "error": str(e)}

def generate_api_docs():
    docs = {"version":"6.0.0","generated":datetime.now().isoformat(),"endpoints":[]}
    for fp in sorted(SRC_DIR.glob("*api*.py")):
        d = parse_api_file(fp)
        if d.get("endpoints"):
            docs["endpoints"].append(d)
    (DOCS_DIR / "api_docs.json").write_text(json.dumps(docs, indent=2))
    return docs

def extract_classes():
    """Extract documented classes for backtest/catalog use."""
    out = []
    for fp in sorted(SRC_DIR.glob("*.py")):
        try:
            tree = ast.parse(fp.read_text())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name[0].isupper():
                doc = (ast.get_docstring(node) or "(no docstring)").splitlines()[0][:120]
                out.append({
                    "file": fp.name,
                    "name": node.name,
                    "doc":  doc,
                    "methods": [m.name for m in node.body
                                if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")],
                })
    (DOCS_DIR / "components.json").write_text(json.dumps(out, indent=2, default=str))
    return out

def generate_readme(components, api_docs):
    n_endpoints = sum(len(d.get("endpoints", [])) for d in api_docs["endpoints"])
    body = f"""# TC Sports Intelligence

**Version:** 6.0.0
**Generated:** {datetime.now().isoformat()}

## Overview
- {len(components)} documented components
- {n_endpoints} API endpoints
- Sports: MLB, WNBA, WC, NBA, NFL, NHL

## Quick Start
```bash
python3 /home/workspace/Projects/daily_picks.py --sport wnba
python3 /home/workspace/Projects/daily_picks.py --sport mlb
streamlit run /home/workspace/Projects/dashboard.py --server.port 8510
```

## Components
"""
    for c in components[:20]:
        body += f"- **{c['name']}** (`{c['file']}`) — {c['doc'].splitlines()[0][:100]}\n"
    (DOCS_DIR / "README.md").write_text(body)
    return body

if __name__ == "__main__":
    api_docs  = generate_api_docs()
    components = extract_classes()
    generate_readme(components, api_docs)
    print(f"✅ Docs written to {DOCS_DIR}  ({len(components)} components, "
          f"{sum(len(d['endpoints']) for d in api_docs['endpoints'])} endpoints)")
