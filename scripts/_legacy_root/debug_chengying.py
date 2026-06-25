"""debug_chengying.py"""
import json
with open(r'D:\codex\V18\test_run_judgment\output_程颖\_internal\distilled_card.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print('=== FactCard parties ===')
for p in data['fact_card'].get('parties', []):
    print(f"  role={p.get('role'):<20} name={p.get('name')}")
print()
print('=== source_refs (前 5) ===')
for sr in data['fact_card'].get('source_refs', [])[:5]:
    print(f"  file: {sr.get('file_name')}")
    print(f"  excerpt: {(sr.get('excerpt') or '')[:200]}")
    print()
print('=== key_facts ===')
for kf in data['fact_card'].get('key_facts', [])[:8]:
    print(f"  - {kf}")
