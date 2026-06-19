"""Extract and display all documents from case 1."""
import sys, os
sys.path.insert(0, ".")
from docx import Document

customer_dir = r"D:\codex\V18\outputs\test_real_case_001\customer"
output_file = r"D:\codex\V18\outputs\test_real_case_001\all_docs_content.txt"

docx_files = sorted([f for f in os.listdir(customer_dir) if f.endswith(".docx")])

with open(output_file, "w", encoding="utf-8") as out:
    for fname in docx_files:
        fpath = os.path.join(customer_dir, fname)
        doc = Document(fpath)
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        
        out.write("=" * 80 + "\n")
        out.write(f"[FILE] {fname}\n")
        out.write("=" * 80 + "\n")
        out.write(full_text)
        out.write("\n\n")

print(f"Done. Output: {output_file}")
print(f"Documents: {len(docx_files)}")
