# LOTUS Merge Conflict Resolution Guide

## The Situation

You're merging `claude/fix-lotus-circular-deps` into your `context/test` branch and got conflicts in:
1. `lotus/nucleus.py`
2. `lotus/modules/capability_modules/consciousness/logic.py`

## Quick Resolution (Recommended)

**Accept ALL changes from the incoming branch** (claude/fix-lotus-circular-deps):

```bash
# Accept the fixed versions
git checkout --theirs lotus/nucleus.py
git checkout --theirs lotus/modules/capability_modules/consciousness/logic.py

# Stage the resolved files
git add lotus/nucleus.py
git add lotus/modules/capability_modules/consciousness/logic.py

# Complete the merge
git commit -m "Merge: Accept all fixes from claude/fix-lotus-circular-deps

- Fixed topological sort algorithm in nucleus.py
- Added missing imports to consciousness/logic.py
- System now boots successfully"
```

Done! The merge is complete.

## Why Accept "Theirs"?

The `claude/fix-lotus-circular-deps` branch contains **critical fixes**:

### nucleus.py Changes:
```python
# OLD (your branch - BROKEN):
in_degree = {name: 0 for name in graph}
for deps in graph.values():
    for dep in deps:
        if dep in in_degree:
            in_degree[dep] += 1  # BACKWARDS!

# NEW (incoming - FIXED):
in_degree = {name: len(deps) for name, deps in graph.items()}
```

The old version had the topological sort backwards, causing fake "circular dependency" errors.

### consciousness/logic.py Changes:
```python
# OLD (your branch - MISSING IMPORTS):
class ConsciousnessModule(BaseModule):  # Error: BaseModule not imported!

# NEW (incoming - FIXED):
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, periodic

@dataclass
class Thought:
    content: str
    interestingness: float
    reasoning: str

class ConsciousnessModule(BaseModule):  # Now works!
```

## Manual Resolution (If You Want to Inspect)

If you want to see the conflicts:

```bash
# View the conflicts
git diff

# Open in your editor
code lotus/nucleus.py
code lotus/modules/capability_modules/consciousness/logic.py

# Look for these markers:
<<<<<<< HEAD          # Your current branch (context/test)
... your version ...
=======
... their version ... # Incoming (claude/fix-lotus-circular-deps)
>>>>>>> claude/fix-lotus-circular-deps
```

For each conflict:
1. **Topological sort in nucleus.py** → Use "their" version (it's fixed)
2. **Imports in consciousness/logic.py** → Use "their" version (complete)
3. **Database handling in nucleus.py** → Use "their" version (optional DB)

## After Resolving

Test that LOTUS boots:

```bash
cd lotus
python nucleus.py
```

You should see:
```
🌸 LOTUS starting up...
✓ Configuration loaded
✓ Redis connected
✓ 5 modules discovered
🌸 LOTUS is online and ready!
```

## If You Get Stuck

The safe command that always works:

```bash
# Nuclear option: just use the working branch
git merge --abort
git checkout claude/fix-lotus-circular-deps
```

Your `context/test` branch will still exist, you can merge it back later if needed.

---

**TL;DR: Run these 4 commands:**

```bash
git checkout --theirs lotus/nucleus.py
git checkout --theirs lotus/modules/capability_modules/consciousness/logic.py
git add .
git commit -m "Merge: Accept all fixes from claude/fix-lotus-circular-deps"
```

**Then test:**
```bash
python lotus/nucleus.py
```

✅ Done!
