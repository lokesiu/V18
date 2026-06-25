"""check_api.py"""
import os
print(f'API_KEY set: {bool(os.environ.get("DEEPSEEK_API_KEY"))}')
print(f'BASE_URL set: {bool(os.environ.get("DEEPSEEK_BASE_URL"))}')
configured = bool(os.environ.get('DEEPSEEK_API_KEY')) and bool(os.environ.get('DEEPSEEK_BASE_URL'))
print(f'API configured: {configured}')
