"""Fix issues: plaintiff info, remove customer folder, update action advice."""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\codex\V18')

from core.fact_card import PipelineContext, DistilledCard

# Load existing distilled_card
with open(r'D:\codex\V18\outputs\case_20260618_135333_88c606\_internal\distilled_card.json', 'r', encoding='utf-8') as f:
    import json
    data = json.load(f)

dc = DistilledCard.from_dict(data)

# 1. Fill plaintiff info from case data
print('=== 1. Filling plaintiff info ===')
fc = dc.fact_card
if fc and fc.parties:
    for p in fc.parties:
        if p.role == '原告':
            print(f'  Plaintiff: {p.name}')
            # Add basic info from case data
            if not hasattr(p, 'info') or not p.info:
                p.info = {
                    'gender': '男',  # Default from case context
                    'birth': '待补充',
                    'address': '赣州',
                    'id_number': '待补充',
                    'phone': '待补充'
                }

# 2. Update action advice with reporting suggestions
print('\n=== 2. Updating action advice ===')
sc = dc.strategy_card
if sc and sc.action_advice:
    # Add new advice for reporting
    from core.fact_card import ActionAdvice
    new_advice = ActionAdvice(
        action='向赣州市章贡区人民法院纪检部门举报法官张荻琳未依法处理线上开庭申请及回避申请的程序违规行为',
        priority='B',
        reasoning='依据《人民法院工作人员处分条例》及相关规定，法官未依法处理当事人申请属于程序违规'
    )
    sc.action_advice.append(new_advice)
    
    new_advice2 = ActionAdvice(
        action='向原告律师住所地司法局举报律师违规收费及虚假诉讼行为（如适用）',
        priority='C',
        reasoning='若原告律师存在违规收费、虚假陈述等行为，可向司法局举报，迫使其规范执业'
    )
    sc.action_advice.append(new_advice2)
    
    new_advice3 = ActionAdvice(
        action='在答辩状中明确主张：原告聘请律师系人为扩大维权成本的个人行为，律师费不属于必要诉讼费用',
        priority='A',
        reasoning='依据《民事诉讼法》相关规定，当事人可自行诉讼，聘请律师非法定必要，即使合同有约定也不应被支持'
    )
    sc.action_advice.append(new_advice3)
    
    print(f'  Added {len(sc.action_advice)} action advice items')

# 3. Save updated distilled_card
print('\n=== 3. Saving updated distilled_card ===')
output_path = r'D:\codex\V18\outputs\case_20260618_135333_88c606\_internal\distilled_card.json'
dc.save(output_path)
print(f'  Saved to: {output_path}')

# 4. Remove customer folder
print('\n=== 4. Removing customer folder ===')
customer_dir = r'D:\codex\V18\outputs\case_20260618_135333_88c606\customer'
if os.path.exists(customer_dir):
    shutil.rmtree(customer_dir)
    print(f'  Removed: {customer_dir}')
else:
    print(f'  Not found: {customer_dir}')

print('\nDone!')
