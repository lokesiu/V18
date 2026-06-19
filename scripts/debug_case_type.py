"""Debug case type derivation."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\codex\V18')
from core.pipeline.step7_render import _derive_case_type
from core.fact_card import FactCard

# Load from JSON
with open(r'D:\codex\V18\outputs\case_20260618_135333_88c606\distilled_card.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fc = FactCard()
fc.key_facts = data['fact_card']['key_facts']
fc.disputed_facts = data['fact_card']['disputed_facts']

result = _derive_case_type(fc)
print(f'Case type: {result}')
print()
print('Checking keywords:')
all_text = ' '.join(fc.key_facts) + ' ' + ' '.join(fc.disputed_facts)
print(f'  垫资 in text: {"垫资" in all_text}')
print(f'  中介 in text: {"中介" in all_text}')
print(f'  合同 in text: {"合同" in all_text}')
print(f'  协议 in text: {"协议" in all_text}')
