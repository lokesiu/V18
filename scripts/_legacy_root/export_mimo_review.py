"""导出 MiMo 复核结果为 markdown."""
import json
from pathlib import Path
from datetime import datetime

# 找最新的输出目录
output_dir = Path(r'D:\codex\V18\test_run\output')
internal_dir = output_dir / '_internal'
review_json_path = internal_dir / 'mimo_review_results.json'

if not review_json_path.exists():
    print(f'No review JSON at {review_json_path}')
    raise SystemExit(1)

data = json.loads(review_json_path.read_text(encoding='utf-8'))
mimo_results = data.get('results', {})

if not mimo_results:
    print('No MiMo review results in JSON')
    print('Keys:', list(data.keys()))
    raise SystemExit(1)

md = f"""# MiMo 专业审校报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**审校 AI**: MiMo v2.5
**被审校 AI**: DeepSeek v4-flash
**文书数量**: {len(mimo_results)}

---

"""

# 总体统计
total_blocking = 0
total_warning = 0
total_info = 0
for doc_type, review in mimo_results.items():
    for issue in review.get('issues', []):
        sev = issue.get('severity', '')
        if sev == 'blocking':
            total_blocking += 1
        elif sev == 'warning':
            total_warning += 1
        elif sev == 'info':
            total_info += 1

md += f"""## 总体统计

| 级别 | 数量 |
|------|------|
| 严重 (blocking) | {total_blocking} |
| 警告 (warning) | {total_warning} |
| 提示 (info) | {total_info} |

---

"""

# 详细列出每份文书的审校结果
for doc_type, review in mimo_results.items():
    score = review.get('overall_score', '?')
    summary = review.get('summary', '(无总结)')
    issues = review.get('issues', [])
    highlights = review.get('highlights', [])

    md += f"""## {doc_type}

**评分**: {score}
**总结**: {summary}

### 问题列表 ({len(issues)} 项)
"""
    if not issues:
        md += "_无问题_\n\n"
    else:
        for issue in issues:
            sev = issue.get('severity', 'info')
            loc = issue.get('location', '(未定位)')
            msg = issue.get('message', '')
            sug = issue.get('suggestion', '')
            sev_emoji = {'blocking': '🚨', 'warning': '⚠️', 'info': '💡'}.get(sev, '•')
            md += f"\n- {sev_emoji} **[{sev.upper()}]** `{loc}`\n"
            md += f"  - 问题: {msg}\n"
            if sug:
                md += f"  - 建议: {sug}\n"

    if highlights:
        md += "\n### 亮点\n"
        for h in highlights:
            md += f"- ✓ {h}\n"

    md += "\n---\n\n"

out_path = output_dir / 'mimo_review_report.md'
out_path.write_text(md, encoding='utf-8')
print(f'Report: {out_path}')
print(f'Size: {len(md)} chars')