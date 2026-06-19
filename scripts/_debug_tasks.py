import sys
sys.path.insert(0, "D:/codex/V18")
from core.task_store import get_task_store
ts = get_task_store()
tasks = ts.list_all()
for t in tasks[-5:]:
    d = t.to_dict()
    print(d.get("task_id", "?"), "|", d.get("status", "?"), "|", d.get("error", ""))
