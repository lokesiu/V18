"""show_chengying_v2.py — 打印生成的文书内容"""
import sys; sys.path.insert(0, '.')

for label, md in [
    ("【锋芒毕露版】", r'D:\codex\V18\test_run_judgment\程颖_答辩状_锋芒毕露.md'),
    ("【笑面虎版】", r'D:\codex\V18\test_run_judgment\程颖_答辩状_笑面虎.md'),
    ("【反诉状】", r'D:\codex\V18\test_run_judgment\程颖_反诉状_超标的保全.md'),
]:
    print("=" * 70)
    print(label)
    print("=" * 70)
    with open(md, 'r', encoding='utf-8') as f:
        content = f.read()
    # 跳过第一行 markdown 标题
    body = content.split('\n', 2)[-1] if content.startswith('# ') else content
    print(body[:3500])
    print("...")
    print()
