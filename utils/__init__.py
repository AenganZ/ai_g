# utils/__init__.py - 유틸리티 모듈 초기화
"""
유틸리티 모듈

공통으로 사용되는 유틸리티 함수들을 제공합니다.
"""

from .logging import (
    append_json_to_file,
    load_logs_from_file,
    get_log_stats,
    clear_logs,
    backup_logs,
    append_log_entry,  # 호환성
    read_logs         # 호환성
)

__all__ = [
    'append_json_to_file',
    'load_logs_from_file', 
    'get_log_stats',
    'clear_logs',
    'backup_logs',
    'append_log_entry',
    'read_logs'
]