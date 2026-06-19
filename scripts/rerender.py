"""Re-render documents using existing distilled_card.json with fixed code."""
import sys, os, json, shutil
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\codex\V18')

from core.fact_card import PipelineContext, DistilledCard

# Load existing distilled_card
with open(r'D:\codex\V18\outputs\case_20260618_135333_88c606\_internal\distilled_card.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

dc = DistilledCard.from_dict(data)
print(f'Loaded distilled_card: case_id={dc.fact_card.case_id}, parties={len(dc.fact_card.parties)}')
print(f'Strategy rating: {dc.strategy_card.sabcd_rating}')
print(f'Evidence gaps: {len(dc.strategy_card.evidence_gap)}')
print(f'Action advice: {len(dc.strategy_card.action_advice)}')

# Create context
ctx = PipelineContext(identity='被诉方（被告）', goal='应诉答辩')
ctx.output_dir = r'D:\codex\V18\outputs\case_20260618_135333_88c606'
ctx.distilled_card = dc
ctx.fact_card = dc.fact_card
ctx.strategy_card = dc.strategy_card

# Delete existing output files to force re-rendering
customer_dir = os.path.join(ctx.output_dir, 'customer')
if os.path.exists(customer_dir):
    shutil.rmtree(customer_dir)
    print(f'Deleted existing customer dir: {customer_dir}')

# Run step6 template fill
print()
print('Running step6_template_fill...')
from core.pipeline.step6_template_fill import step6_template_fill
ctx = step6_template_fill(ctx)
filled = getattr(ctx, '_filled_templates', {})
print(f'Filled templates: {len(filled)}')

# Run step6 LLM generate (skip if no API)
print()
print('Running step6_llm_generate...')
from core.pipeline.step6_llm_generate import step6_llm_generate
ctx = step6_llm_generate(ctx)
llm_docs = getattr(ctx, '_llm_generated_docs', {})
print(f'LLM docs: {len(llm_docs)}')

# Run step7 render
print()
print('Running step7_render...')
from core.pipeline.step7_render import step7_render
ctx = step7_render(ctx)
rendered = getattr(ctx, '_rendered_files', [])
print(f'Rendered files: {len(rendered)}')

# Print logs
print()
print('=== Logs ===')
for log in ctx.logs:
    print(f'  {log}')

print()
print('Done!')
