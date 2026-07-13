#!/usr/bin/env python3
"""Replace bare 'except: pass' with 'except Exception as e: logger.debug(...)' in all .py files."""
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("fix_silent_passes")

ROOT = Path("/home/workspace/Projects")
fixed = 0
for py in ROOT.rglob("*.py"):
    if "__pycache__" in str(py) or py.name == "fix_silent_passes.py":
        continue
    txt = py.read_text()
    new = re.sub(
        r"(\bexcept\s+Exception\s*:\s*\n)(\s+)pass(\s*)$",
        lambda m: f'{m.group(1)}{m.group(2)}import logging as _log\n{m.group(2)}_log.getLogger(__name__).debug("exception", exc_info=True){m.group(3)}',
        txt,
        flags=re.MULTILINE,
    )
    if new != txt:
        py.write_text(new)
        fixed += 1
        log.info("fixed %s", py)
print(f"Fixed {fixed} files")
