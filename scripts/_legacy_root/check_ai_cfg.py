"""check_ai_cfg.py"""
import sys
sys.path.insert(0, '.')
from core.ai_config import get_ai_config, is_api_configured
cfg = get_ai_config()
print(f'api_key configured: {bool(cfg.api_key)}')
print(f'api_key prefix: {cfg.api_key[:8] if cfg.api_key else "EMPTY"}')
print(f'base_url: {cfg.base_url}')
print(f'is_api_configured: {is_api_configured()}')
