"""Extract defense document from v2."""
import sys, os
sys.path.insert(0, ".")
from docx import Document

doc_path = r"D:\codex\V18\outputs\test_real_case_001_v2\customer\06_答辩状_上海嘉忞贸易有限公司案.docx"
doc = Document(doc_path)
full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

output = r"D:\codex\V18\outputs\test_real_case_001_v2\defense_v2.txt"
with open(output, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Done. Length: {len(full_text)} chars")

# Check for hardcoded content
checks = ["赣州市", "李林", "垫资协议", "张荻琳", "4万元违约金"]
for c in checks:
    found = c in full_text
    print(f"  Hardcoded '{c}': {'FOUND (BAD)' if found else 'NOT FOUND (GOOD)'}")
