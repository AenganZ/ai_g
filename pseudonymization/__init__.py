# pseudonymization/__init__.py - normalizers.py 전용 버전
"""
GenAI Pseudonymizer (AenganZ Enhanced) - normalizers.py 통합 버전

주요 기능:
- normalizers.py 하나로 탐지 + 정규화 통합
- 실제 가명 치환 (김가명, 이가명 등)
- 강화된 PII 탐지 (이메일, 전화번호, 이름, 주소, 나이)
- 스마트 주소 처리 (첫 번째 주소만 치환)
- 일반명사 필터링 (고객, 손님 등 제외)
"""

# 핵심 함수들 (core.py)
from .core import (
    pseudonymize_text,
    pseudonymize_text_with_fake,
    restore_original,
    get_data_pool_stats
)

# 데이터풀 (pools.py)
from .pools import (
    get_pools,
    initialize_pools,
    NAME_EXCLUDE_WORDS
)

# PII 탐지 (normalizers.py에서 통합)
from .normalizers import (
    detect_pii_all,
    detect_emails,
    detect_phones,
    detect_names,
    detect_addresses,
    detect_ages,
    # 호환성 함수들
    detect_pii_enhanced,
    detect_with_ner,
    detect_with_regex,
    detect_names_from_csv,
    detect_addresses_from_csv,
    merge_detections
)

# 매니저 (manager.py)
from .manager import (
    get_manager,
    is_manager_ready,
    get_manager_status
)

# 버전 정보
__version__ = "4.1.0"  # normalizers 통합 버전
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced) - Normalizers Unified"
__description__ = "AI 서비스용 개인정보 가명화 시스템 (normalizers.py 통합 버전)"
__author__ = "AenganZ Development Team"

# 공개 API
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'pseudonymize_text_with_fake',
    'restore_original',
    'get_data_pool_stats',
    
    # 데이터풀
    'get_pools',
    'initialize_pools',
    'NAME_EXCLUDE_WORDS',
    
    # PII 탐지 (normalizers.py 통합)
    'detect_pii_all',
    'detect_emails',
    'detect_phones', 
    'detect_names',
    'detect_addresses',
    'detect_ages',
    'detect_pii_enhanced',  # 호환성
    'detect_with_ner',      # 호환성
    'detect_with_regex',    # 호환성
    'detect_names_from_csv', # 호환성
    'detect_addresses_from_csv', # 호환성
    'merge_detections',     # 호환성
    
    # 매니저
    'get_manager',
    'is_manager_ready',
    'get_manager_status',
    
    # 메타데이터
    '__version__',
    '__title__',
    '__description__',
    '__author__'
]

def print_info():
    """정보 출력"""
    print(f"{__title__} v{__version__}")
    print(f"{__description__}")
    print(f"작성자: {__author__}")
    print()
    print("주요 변경사항:")
    print("  - detection.py 제거")
    print("  - normalizers.py 하나로 탐지 + 정규화 통합")
    print("  - 더 간단하고 안정적인 구조")
    print()
    print("주요 기능:")
    print("  - 실제 가명 치환 (김가명, 이가명 등)")
    print("  - 강화된 PII 탐지 (이메일, 전화번호, 이름, 주소, 나이)")
    print("  - 스마트 주소 처리 (첫 번째 주소만 치환)")
    print("  - 일반명사 필터링 (고객, 손님 등 제외)")
    print("  - Flask 기반 서버 호환")
    print()
    print("사용법:")
    print("  from pseudonymization import pseudonymize_text_with_fake")
    print("  result = pseudonymize_text_with_fake('김철수 고객님')")
    print("  print(result['pseudonymized_text'])")