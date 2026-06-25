"""check_case_id.py"""
import sys; sys.path.insert(0, '.')
from core.fact_card import FactCard
fc = FactCard(case_id='(2026)苏0115民初5112号', court='test')
print(f'fc.case_id = {fc.case_id!r}')
print(f'startswith (: {fc.case_id.startswith("(")}')
print(f'endswith ): {fc.case_id.endswith(")")}')
