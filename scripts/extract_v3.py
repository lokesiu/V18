import sys, os
sys.path.insert(0, ".")
from docx import Document

doc_path = r"D:\codex\V18\outputs\test_real_case_001_v3\customer\06_答辩状_上海嘉忞贸易有限公司案.docx"
doc = Document(doc_path)
full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

output = r"D:\codex\V18\outputs\test_real_case_001_v3\defense_v3.txt"
with open(output, "w", encoding="utf-8") as f:
    f.write(full_text)
print(f"Done. {len(full_text)} chars")
