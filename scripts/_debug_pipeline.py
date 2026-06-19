"""Direct pipeline test — replicate what the worker does."""
import sys
sys.path.insert(0, "D:/codex/V18")

import os
from pathlib import Path
from datetime import datetime

# Find latest case output
outputs = Path("outputs")
cases = sorted([d for d in outputs.iterdir() if d.is_dir() and d.name.startswith("case_20260618")], reverse=True)
if not cases:
    print("No cases found")
    sys.exit(1)

latest = cases[0]
print(f"Latest case: {latest.name}")

# Check what files were uploaded
from core.task_store import get_task_store
ts = get_task_store()
tasks = ts.list_all()
print(f"Tasks in store: {len(tasks)}")
for t in tasks[-3:]:
    d = t.to_dict()
    print(f"  {d.get('task_id')} | status={d.get('status')} | files={d.get('file_count')}")

# Try to find uploaded files
import glob
jpg_files = glob.glob("D:/Downloads/*.jpg") + glob.glob("D:/Desktop/*.jpg") + glob.glob("D:/Pictures/*.jpg")
print(f"\nJPG files found in common dirs: {len(jpg_files)}")

# Check the home page uploaded files pattern
# The worker gets files from home_page.upload_card.selected_files
# These are the actual file paths the user selected

# Let's check the latest output dir structure
print(f"\nLatest case dir contents:")
for item in latest.rglob("*"):
    print(f"  {item.relative_to(latest)} ({item.stat().st_size if item.is_file() else 'dir'})")

# Try running intake on the latest case's input
# First, find what input_dir the worker used
# The worker sets input_dir = str(Path(self.files[0]).parent)
# We need to find the original files

# Check if there's a manifest or any metadata
manifest_path = latest / "_internal" / "ai_run_manifest.json"
if manifest_path.exists():
    import json
    with open(manifest_path) as f:
        manifest = json.load(f)
    print(f"\nManifest: {json.dumps(manifest, indent=2)}")
else:
    print("\nNo manifest found")

# Check task store for error details
print("\nAll tasks with errors:")
for t in tasks:
    d = t.to_dict()
    if d.get("error"):
        print(f"  {d.get('task_id')} | error={d.get('error')}")
